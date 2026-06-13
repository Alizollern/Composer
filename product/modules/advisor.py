"""M6 — «Цифровой опер-дир»: агент, который САМ собирает ответ из данных компании.

Это первый многошаговый агент Evergreen (а не одиночный вызов LLM). Владелец
задаёт свободный вопрос — «Какая точка проседает и что делать?», «Чего не хватает
в стандартах?» — и агент через инструменты сам ходит в данные компании:
стандарты (RAG), отзывы/точки (командный центр), пробелы (вопросы без ответа),
а затем собирает деловой ответ собственнику.

Инструменты read-only и СКОУПЯТСЯ на компанию (мультитенант): каждый замкнут на
(db, company_id), переданные из токена. Движок остаётся generic — домен здесь.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from product import brain
from product.db import models as m
from product.modules import reviews as reviews_mod
from product.rag import get_embedder, search_chunks
from product.rag.embedder import Embedder

_SYSTEM = (
    "Ты — цифровой операционный директор сети для собственника бизнеса. "
    "Отвечаешь на вопросы владельца строго по ДАННЫМ компании, которые получаешь "
    "через инструменты, а не по догадкам.\n"
    "Как работать:\n"
    "1) Сначала собери факты инструментами: network_overview (сеть точек), "
    "point_problems (боли конкретной точки), search_standards (что написано в "
    "регламентах), list_gaps (чего не хватает в стандартах).\n"
    "2) Не выдумывай: если данных нет — так и скажи.\n"
    "3) Ответ давай кратко и по-деловому: сначала ВЫВОД, затем 2–4 пункта "
    "обоснования по фактам, затем КОНКРЕТНЫЕ действия управляющему.\n"
    "Пиши простым деловым русским, как живой опер-директор в отчёте собственнику."
)


def _find_point(points: List[m.Point], needle: str) -> Optional[m.Point]:
    """Найти точку по id или по подстроке названия (без регистра)."""
    needle = (needle or "").strip().lower()
    if not needle:
        return None
    for p in points:
        if p.id == needle:
            return p
    for p in points:
        if needle in (p.name or "").lower():
            return p
    return None


def build_tools(db: Session, company_id: str, *,
                embedder: Optional[Embedder] = None) -> List[dict]:
    """Собрать набор read-only инструментов, замкнутых на компанию."""
    emb = embedder or get_embedder()

    def search_standards(query: str) -> str:
        query = (query or "").strip()
        if not query:
            return "Уточни запрос для поиска по стандартам."
        try:
            vec = emb.embed_one(query)
            hits = search_chunks(db, company_id, vec, top_k=4)
        except Exception as e:
            return f"Поиск по стандартам недоступен: {e}"
        if not hits:
            return "В опубликованных стандартах ничего не найдено по этому запросу."
        return "\n\n".join(
            f"• «{h.document_title}» (близость {h.score:.2f}):\n{h.text[:500]}"
            for h in hits)

    def network_overview() -> str:
        cc = reviews_mod.command_center(db, company_id)
        pts = cc.get("points") or []
        if not pts:
            return "Нет подключённых точек — отзывы ещё не собираются."
        pulse = cc["pulse"]
        lines = [
            f"Точек в сети: {len(pts)}. Пульс всей сети: отзывов {pulse['total']}, "
            f"средняя оценка {pulse['avg_rating']}, негатив {pulse['negative']}, "
            f"жалоб {pulse['complaints']}.",
            "По точкам:",
        ]
        for p in pts:
            lines.append(
                f"- {p['name']}: отзывов {p['reviews_count']}, средняя "
                f"{p['avg_rating']}, негатив {p['negative_count']}, "
                f"жалоб {p['complaints_count']}.")
        return "\n".join(lines)

    def point_problems(point: str) -> str:
        pts = reviews_mod.list_points(db, company_id)
        if not pts:
            return "Нет подключённых точек."
        match = _find_point(pts, point)
        if not match:
            return ("Точка не найдена. Доступные точки: "
                    + ", ".join(p.name for p in pts))
        cc = reviews_mod.command_center(db, company_id, point_id=match.id)
        probs = cc.get("problems") or []
        if not probs:
            return f"У точки «{match.name}» жалоб не найдено — работает штатно."
        out = [f"Главные боли точки «{match.name}»:"]
        for pr in probs[:6]:
            sample = pr["samples"][0] if pr.get("samples") else ""
            out.append(
                f"- {pr['title']} — {pr['count']} жалоб(ы). "
                f"Рекомендация: {pr.get('recommendation') or '—'}. "
                f"Пример отзыва: «{sample}»")
        return "\n".join(out)

    def list_gaps() -> str:
        rows = db.execute(
            select(m.QAGap)
            .where(m.QAGap.company_id == company_id, m.QAGap.resolved.is_(False))
            .order_by(m.QAGap.created_at.desc()).limit(20)
        ).scalars().all()
        if not rows:
            return "Пробелов не зафиксировано — на вопросы сотрудников ответы находились."
        return ("Вопросы сотрудников, на которые в стандартах НЕ нашлось ответа "
                "(пробелы в регламентах):\n"
                + "\n".join(f"- {g.question}" for g in rows))

    return [
        {"schema": {
            "name": "search_standards",
            "description": ("Найти релевантные фрагменты во внутренних стандартах/"
                            "регламентах компании по ключевым словам."),
            "input_schema": {"type": "object", "properties": {
                "query": {"type": "string", "description": "ключевые слова запроса"}},
                "required": ["query"]}},
         "fn": lambda i: search_standards(i.get("query", ""))},
        {"schema": {
            "name": "network_overview",
            "description": ("Сводка по всей сети точек: пульс и метрики каждой "
                            "точки (средняя оценка, негатив, число жалоб)."),
            "input_schema": {"type": "object", "properties": {}}},
         "fn": lambda i: network_overview()},
        {"schema": {
            "name": "point_problems",
            "description": ("Главные жалобы конкретной точки (по названию) с "
                            "рекомендациями и примерами отзывов."),
            "input_schema": {"type": "object", "properties": {
                "point": {"type": "string", "description": "название точки"}},
                "required": ["point"]}},
         "fn": lambda i: point_problems(i.get("point", ""))},
        {"schema": {
            "name": "list_gaps",
            "description": ("Вопросы сотрудников, на которые в стандартах нет "
                            "ответа — пробелы в регламентах."),
            "input_schema": {"type": "object", "properties": {}}},
         "fn": lambda i: list_gaps()},
    ]


def ask(db: Session, company_id: str, question: str, *, llm=None,
        embedder: Optional[Embedder] = None, on_event=None,
        max_steps: int = 8) -> dict:
    """Задать вопрос цифровому опер-диру. Возвращает {"answer": str}."""
    question = (question or "").strip()
    if not question:
        return {"answer": "Задайте вопрос — например: «Какая точка проседает и что делать?»"}
    tools = build_tools(db, company_id, embedder=embedder)
    answer = brain.run_tools_agent(
        _SYSTEM, question, tools, llm=llm, company=company_id,
        max_steps=max_steps, on_event=on_event)
    return {"answer": answer}
