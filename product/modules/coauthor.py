"""M8 — «AI-соавтор стандартов»: помогает собственнику держать регламенты живыми.

Две задачи живого опер-дира, которые тут оцифрованы:
  1) НАЙТИ ДЫРЫ. Бот копит «пробелы» (QAGap) — реальные вопросы сотрудников, на
     которые не нашлось ответа в базе. Соавтор группирует их в темы и предлагает,
     какой стандарт стоит дописать. Грунт — НАСТОЯЩИЕ вопросы людей, поэтому
     потребность не выдумана; модель лишь раскладывает их по полкам.
  2) НАПИСАТЬ ЧЕРНОВИК. По теме/указанию собственник получает черновик стандарта
     (заголовок + категория + текст), который потом сам проверяет и сохраняет
     обычным созданием документа (черновик, не публикуем автоматически).

Антигаллюцинация: в «найти дыры» мы НЕ даём модели выдумывать вопросы — после
ответа отбрасываем любые «примеры», которых не было во входных пробелах. В
«написать черновик» текст пишет модель (иначе никак), но это ЧЕРНОВИК для ревью
человеком, и сохраняется он отдельным осознанным действием владельца.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from product import brain
from product.agent_log import log_event
from product.db import models as m
from product.modules import chat as chat_mod

MAX_GAPS = 40  # сколько последних пробелов отдаём модели за раз


class CoAuthorError(Exception):
    """Не удалось собрать предложение/черновик (например, модель недоступна)."""


# ----------------------------- Найти дыры ------------------------------------

_SUGGEST_SYSTEM = (
    "Ты — операционный директор сети. Тебе дают ПРОНУМЕРОВАННЫЙ список реальных "
    "вопросов сотрудников, на которые в базе знаний не нашлось ответа. Сгруппируй "
    "их в 2-6 тем и для каждой предложи, какой стандарт стоит написать.\n"
    "Верни РОВНО валидный JSON-массив без markdown и пояснений. Каждый элемент:\n"
    '{"title": "название будущего стандарта", "rationale": "зачем нужен, 1 фраза", '
    '"question_numbers": [номера вопросов из списка]}\n'
    "Используй ТОЛЬКО номера из данного списка. Не придумывай вопросов."
)


def _unresolved_gaps(db: Session, company_id: str) -> List[m.QAGap]:
    gaps = chat_mod.list_gaps(db, company_id, resolved=False)
    return gaps[:MAX_GAPS]


def suggest_from_gaps(db: Session, company_id: str, *, llm=None) -> dict:
    """Предложить, какие стандарты дописать, исходя из реальных пробелов.

    Возвращает {has_gaps, count, suggestions:[{title, rationale, questions:[...]}]}.
    Без модели/при сбое — честный запасной режим: каждый пробел как отдельная
    тема (никаких выдуманных группировок)."""
    gaps = _unresolved_gaps(db, company_id)
    if not gaps:
        return {"has_gaps": False, "count": 0, "suggestions": []}

    questions = [g.question.strip() for g in gaps if g.question and g.question.strip()]
    numbered = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))

    suggestions: List[dict] = []
    try:
        data = brain.complete_json(_SUGGEST_SYSTEM, numbered, expect="array",
                                   llm=llm, operation="coauthor_suggest",
                                   company=company_id)
        for item in data:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            nums = item.get("question_numbers") or []
            picked = []
            for n in nums:
                try:
                    idx = int(n) - 1
                except (TypeError, ValueError):
                    continue
                if 0 <= idx < len(questions):  # только реальные вопросы
                    picked.append(questions[idx])
            suggestions.append({
                "title": title,
                "rationale": str(item.get("rationale", "")).strip(),
                "questions": picked[:5],
            })
    except Exception:
        suggestions = []

    if not suggestions:  # запасной режим — без группировки, без выдумок
        for q in questions[:8]:
            suggestions.append({
                "title": f"Стандарт по теме: {q[:60]}",
                "rationale": "Сотрудники спрашивали — ответа в базе нет.",
                "questions": [q],
            })

    log_event("coauthor.suggest", company=company_id,
              gaps=len(questions), suggestions=len(suggestions))
    return {"has_gaps": True, "count": len(questions), "suggestions": suggestions}


# --------------------------- Написать черновик -------------------------------

_DRAFT_SYSTEM = (
    "Ты — операционный директор сети. Напиши ВНУТРЕННИЙ РЕГЛАМЕНТ компании по теме, "
    "которую укажет собственник. Стиль — как у других стандартов: деловой, по пунктам "
    "(1., 1.1., 1.2. …), конкретные действия и цифры, без воды и маркетинга.\n"
    "Верни РОВНО валидный JSON-объект без markdown:\n"
    '{"title": "краткий заголовок стандарта", "category": "кому адресован, 1-3 слова", '
    '"content": "полный текст регламента с нумерацией пунктов"}\n'
    "Если в указании собственника есть конкретные правила — отрази их. Не выдумывай "
    "юридических обязательств и точных сумм, если их не дали; пиши [уточнить] вместо них."
)


def _existing_titles(db: Session, company_id: str, limit: int = 12) -> List[str]:
    stmt = (select(m.Document.title).where(m.Document.company_id == company_id)
            .order_by(m.Document.created_at.desc()).limit(limit))
    return [t for t in db.execute(stmt).scalars().all() if t]


def draft_standard(db: Session, company_id: str, *, instruction: str, llm=None) -> dict:
    """Сгенерировать ЧЕРНОВИК стандарта по указанию собственника.

    Возвращает {title, category, content}. Это черновик для ревью человеком —
    не сохраняется автоматически. Требует рабочую модель; на сбое — CoAuthorError."""
    instruction = (instruction or "").strip()
    if not instruction:
        raise CoAuthorError("Опишите, про что должен быть стандарт.")

    existing = _existing_titles(db, company_id)
    ctx = ""
    if existing:
        ctx = ("\n\nУ компании уже есть стандарты (для единообразия стиля, "
               "не повторяй их дословно):\n- " + "\n- ".join(existing))
    user = f"Тема/указание собственника:\n{instruction}{ctx}"

    try:
        data = brain.complete_json(_DRAFT_SYSTEM, user, expect="object",
                                   llm=llm, operation="coauthor_draft",
                                   company=company_id)
    except Exception as e:
        raise CoAuthorError(f"Не удалось собрать черновик: {e}")

    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()
    if not title or not content:
        raise CoAuthorError("Модель вернула пустой черновик.")

    log_event("coauthor.draft", company=company_id, title=title, chars=len(content))
    return {
        "title": title[:255],
        "category": str(data.get("category", "")).strip()[:120],
        "content": content,
    }


# --------------------------- Закрыть пробел ----------------------------------

def resolve_gap(db: Session, company_id: str, gap_id: str) -> bool:
    """Отметить пробел закрытым (когда стандарт дописан). Идемпотентно."""
    gap = db.get(m.QAGap, gap_id)
    if gap is None or gap.company_id != company_id:
        raise KeyError("Пробел не найден")
    gap.resolved = True
    db.commit()
    log_event("coauthor.resolve_gap", company=company_id, gap=gap_id)
    return True
