"""
M2 — Чат-бот по базе знаний (строгий RAG, приоритет P0).

Контракт (ТЗ): бот отвечает сотруднику ТОЛЬКО на основе стандартов его компании
и ссылается на источник. Если ответа в базе нет — НЕ выдумывает: честно говорит
«этого нет в стандартах» и логирует пробел (QAGap) для собственника.

Два рубежа защиты от выдумок:
  1) Retrieval-гейт. Если лучший косинус ниже порога (min_score) — считаем, что
     релевантного стандарта нет: сразу отказ + лог пробела, LLM даже не зовём.
  2) Generation-гейт. Если фрагменты есть, передаём их модели со строгой
     инструкцией; модель обязана либо ответить по ним со ссылкой, либо вернуть
     маркер отказа. Маркер → тоже отказ + лог пробела.

Вся история (вопрос и ответ) сохраняется в chat_messages; ответ несёт sources —
на какие документы он опирается.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from product import brain
from product.agent_log import log_event
from product.db import models as m
from product.rag import get_embedder, search_chunks
from product.rag.embedder import Embedder
from product.rag.search import SearchHit

# Маркер отказа: модель возвращает ровно его, если в фрагментах нет ответа.
REFUSAL_MARKER = "НЕТ_В_СТАНДАРТАХ"

# Текст отказа для пользователя (и retrieval-, и generation-гейт).
REFUSAL_TEXT = (
    "В стандартах компании нет ответа на этот вопрос. "
    "Я зафиксировал его для руководителя — ответ появится после обновления базы знаний."
)

# Минимальная близость, ниже которой считаем, что релевантного стандарта нет.
DEFAULT_MIN_SCORE = 0.25

_SYSTEM = (
    "Ты — корпоративный ассистент сети. Отвечай СТРОГО и ТОЛЬКО на основе "
    "приведённых ниже фрагментов стандартов компании. Запрещено использовать "
    "общие знания и что-либо додумывать.\n"
    "- Если ответ содержится во фрагментах — дай его кратко и по делу на русском "
    "и в конце укажи источник в виде: Источник: «<название документа>».\n"
    f"- Если ответа во фрагментах НЕТ — верни ровно одну строку: {REFUSAL_MARKER}\n"
    "Не придумывай источники и факты, которых нет во фрагментах."
)


def _build_context(hits: List[SearchHit]) -> str:
    """Собрать нумерованный блок фрагментов для подстановки в промпт."""
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[Фрагмент {i}] Документ: «{h.document_title}»\n{h.text}")
    return "\n\n".join(blocks)


def _dedup_sources(hits: List[SearchHit]) -> List[dict]:
    """Уникальные источники (по документу) для приложения к ответу."""
    seen = set()
    sources: List[dict] = []
    for h in hits:
        if h.document_id in seen:
            continue
        seen.add(h.document_id)
        sources.append({
            "document_id": h.document_id,
            "document_title": h.document_title,
            "score": round(h.score, 4),
        })
    return sources


def _log_gap(db: Session, company_id: str, user_id: Optional[str],
             question: str, best_score: float) -> m.QAGap:
    gap = m.QAGap(company_id=company_id, user_id=user_id,
                  question=question, best_score=best_score)
    db.add(gap)
    return gap


def _save_turn(db: Session, company_id: str, user_id: Optional[str],
               question: str, answer: str, sources: List[dict]) -> None:
    db.add(m.ChatMessage(company_id=company_id, user_id=user_id,
                         role="user", content=question, sources=[]))
    db.add(m.ChatMessage(company_id=company_id, user_id=user_id,
                         role="assistant", content=answer, sources=sources))


def answer_question(
    db: Session,
    company_id: str,
    question: str,
    *,
    user_id: Optional[str] = None,
    top_k: int = 5,
    min_score: float = DEFAULT_MIN_SCORE,
    enforce_audience: bool = False,
    user_role: Optional[str] = None,
    user_point_id: Optional[str] = None,
    embedder: Optional[Embedder] = None,
    llm=None,
) -> dict:
    """Ответить на вопрос сотрудника по строгому RAG.

    enforce_audience=True (для сотрудника) ограничивает ретривал документами его
    аудитории (M1.5) по user_role/user_point_id — бот не «протечёт» стандартом
    чужой роли/точки. Для управляющего/owner выключено (видят всю базу).

    Возвращает dict:
      {"answer", "refused": bool, "sources": [...], "gap_id": str|None, "best_score"}
    Побочно: сохраняет реплики в историю; при отказе — логирует QAGap.
    """
    embedder = embedder or get_embedder()
    q_vec = embedder.embed_one(question)

    allowed_ids = None
    if enforce_audience:
        from product.modules import knowledge as kb
        allowed_ids = kb.visible_document_ids(
            db, company_id, role=user_role, point_id=user_point_id)

    hits = search_chunks(db, company_id, q_vec, top_k=top_k,
                         allowed_document_ids=allowed_ids)
    best_score = hits[0].score if hits else 0.0

    # В журнал агента: что нашёл ретривал (для контроля «на чём думает» бот).
    log_event(
        "chat.retrieval", company=company_id, question=question,
        best_score=round(best_score, 4), min_score=min_score,
        candidates=[{"title": h.document_title, "score": round(h.score, 4)}
                    for h in hits],
    )

    # Рубеж 1 — retrieval-гейт: ничего релевантного не нашли.
    if not hits or best_score < min_score:
        log_event("chat.decision", company=company_id, question=question,
                  decision="refused", gate="retrieval", best_score=round(best_score, 4))
        gap = _log_gap(db, company_id, user_id, question, best_score)
        _save_turn(db, company_id, user_id, question, REFUSAL_TEXT, [])
        db.commit()
        return {"answer": REFUSAL_TEXT, "refused": True, "sources": [],
                "gap_id": gap.id, "best_score": best_score}

    # Рубеж 2 — generation-гейт: даём модели только фрагменты.
    context = _build_context(hits)
    user_prompt = (
        f"Фрагменты стандартов:\n\n{context}\n\n"
        f"Вопрос сотрудника: {question}"
    )
    raw = brain.complete(_SYSTEM, user_prompt, llm=llm,
                         operation="chat_strict_rag", company=company_id).strip()

    if REFUSAL_MARKER in raw or not raw:
        log_event("chat.decision", company=company_id, question=question,
                  decision="refused", gate="generation", best_score=round(best_score, 4))
        gap = _log_gap(db, company_id, user_id, question, best_score)
        _save_turn(db, company_id, user_id, question, REFUSAL_TEXT, [])
        db.commit()
        return {"answer": REFUSAL_TEXT, "refused": True, "sources": [],
                "gap_id": gap.id, "best_score": best_score}

    sources = _dedup_sources(hits)
    log_event("chat.decision", company=company_id, question=question,
              decision="answered", gate="generation", best_score=round(best_score, 4),
              sources=[src["document_title"] for src in sources])
    _save_turn(db, company_id, user_id, question, raw, sources)
    db.commit()
    return {"answer": raw, "refused": False, "sources": sources,
            "gap_id": None, "best_score": best_score}


def list_gaps(db: Session, company_id: str, *, resolved: Optional[bool] = None):
    """«Вопросы без ответа» компании — карта пробелов в стандартах (для owner)."""
    from sqlalchemy import select
    stmt = select(m.QAGap).where(m.QAGap.company_id == company_id)
    if resolved is not None:
        stmt = stmt.where(m.QAGap.resolved == resolved)
    stmt = stmt.order_by(m.QAGap.created_at.desc())
    return list(db.execute(stmt).scalars().all())
