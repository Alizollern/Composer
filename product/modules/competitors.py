"""Конкурентная разведка опер-дира: кто рядом, чем лучше, где слабее.

Для каждой нашей точки храним соседние заведения (Competitor) и сравниваем нашу
точку с ними по рейтингу. Цифры считаем детерминированно — модель тут не нужна,
а значит экран всегда наполнен, быстрый и бесплатный, и ничего не выдумывает.

Шов источника (CompetitorSource) — как у отзывов: офлайн/демо берут фейковый
набор, прод с ключом 2GIS — реальный каталог.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from product.db import models as m
from product.modules import reviews as reviews_mod
from product.reviews.competitor_source import (
    CompetitorSource, get_competitor_source,
)


class CompetitorError(Exception):
    """Понятная пользователю ошибка работы с конкурентами."""


def sync_competitors(db: Session, company_id: str, point_id: str, *,
                     source: Optional[CompetitorSource] = None,
                     limit: int = 10) -> dict:
    """Найти конкурентов рядом с точкой и сохранить (дедуп/обновление).

    Возвращает {"added": int, "updated": int, "total": int}."""
    point = reviews_mod.get_point(db, company_id, point_id)  # бросит KeyError, если чужая
    src = source or get_competitor_source()
    if not point.external_id:
        raise CompetitorError(
            "У точки не указана ссылка на 2GIS — нечего искать рядом.")

    raw = src.find(point.external_id, limit=limit)

    existing = {c.external_id: c for c in _list(db, company_id, point_id)}
    added = updated = 0
    for rc in raw:
        cur = existing.get(rc.external_id)
        if cur is None:
            db.add(m.Competitor(
                company_id=company_id, point_id=point_id, source=src.name,
                external_id=rc.external_id, name=rc.name, address=rc.address,
                distance_m=rc.distance_m, rating=rc.rating,
                reviews_count=rc.reviews_count,
                strengths=list(rc.strengths), weaknesses=list(rc.weaknesses)))
            added += 1
        else:
            cur.name = rc.name
            cur.address = rc.address
            cur.distance_m = rc.distance_m
            cur.rating = rc.rating
            cur.reviews_count = rc.reviews_count
            cur.strengths = list(rc.strengths)
            cur.weaknesses = list(rc.weaknesses)
            updated += 1
    db.commit()
    return {"added": added, "updated": updated, "total": added + len(existing)}


def _list(db: Session, company_id: str, point_id: str) -> List[m.Competitor]:
    return db.execute(
        select(m.Competitor)
        .where(m.Competitor.company_id == company_id,
               m.Competitor.point_id == point_id)
        .order_by(m.Competitor.rating.desc())
    ).scalars().all()


def _competitor_out(c: m.Competitor) -> dict:
    return {
        "id": c.id, "name": c.name, "address": c.address,
        "distance_m": c.distance_m, "rating": round(c.rating, 1),
        "reviews_count": c.reviews_count,
        "strengths": list(c.strengths or []),
        "weaknesses": list(c.weaknesses or []),
    }


def _verdict(my_rating: float, best: float) -> tuple[str, str]:
    """Короткий вердикт по разнице рейтингов (status, текст)."""
    if not my_rating or not best:
        return "unknown", "Недостаточно данных для сравнения."
    gap = round(best - my_rating, 1)
    if gap <= 0:
        return "leading", f"Мы лидер района (+{abs(gap)} к лучшему конкуренту)."
    if gap >= 1.0:
        return "behind", f"Сильно проигрываем: −{gap} к лучшему конкуренту."
    return "close", f"Отстаём на {gap} от лучшего конкурента."


def _point_competition(db: Session, company_id: str, point_meta: dict) -> dict:
    """Собрать сравнение одной нашей точки с её конкурентами."""
    comps = _list(db, company_id, point_meta["id"])
    my_rating = point_meta.get("avg_rating") or 0.0
    best = max((c.rating for c in comps), default=0.0)
    status, verdict = _verdict(my_rating, best)

    # Где конкуренты сильнее нас (их сильные стороны — наши зоны роста) и где у
    # нас преимущество (их слабые стороны).
    their_strengths: list = []
    their_weaknesses: list = []
    for c in comps:
        for s in (c.strengths or []):
            if s not in their_strengths:
                their_strengths.append(s)
        for w in (c.weaknesses or []):
            if w not in their_weaknesses:
                their_weaknesses.append(w)

    ahead = sum(1 for c in comps if my_rating and my_rating >= c.rating)
    return {
        "point_id": point_meta["id"],
        "point_name": point_meta["name"],
        "my_rating": round(my_rating, 1),
        "my_reviews_count": point_meta.get("reviews_count", 0),
        "best_competitor_rating": round(best, 1),
        "competitors_count": len(comps),
        "ahead_of": ahead,                 # скольких конкурентов мы обходим
        "status": status,
        "verdict": verdict,
        "opportunities": their_strengths[:5],   # чему поучиться / что догнать
        "advantages": their_weaknesses[:5],     # на что давить против них
        "competitors": [_competitor_out(c) for c in comps],
    }


def build_view(db: Session, company_id: str, *,
               point_id: Optional[str] = None) -> dict:
    """Экран «Конкуренты»: сравнение наших точек с соседями.

    point_id — если задан, только эта точка; иначе все точки сети."""
    cc = reviews_mod.command_center(db, company_id)
    points = cc.get("points") or []
    if point_id:
        points = [p for p in points if p["id"] == point_id]

    blocks = [_point_competition(db, company_id, p) for p in points]
    # Точки, где отстаём — наверх (там горит).
    order = {"behind": 0, "close": 1, "unknown": 2, "leading": 3}
    blocks.sort(key=lambda b: (order.get(b["status"], 9), -b["competitors_count"]))

    has_data = any(b["competitors_count"] > 0 for b in blocks)
    return {
        "has_data": has_data,
        "points": blocks,
        "summary": _summary(blocks) if has_data else (
            "Конкуренты ещё не подгружены. Нажмите «Найти конкурентов» на точке."),
    }


def _summary(blocks: List[dict]) -> str:
    """Детерминированный брифинг по конкурентной картине сети."""
    behind = [b for b in blocks if b["status"] in ("behind", "close")]
    leading = [b for b in blocks if b["status"] == "leading"]
    parts: list = []
    if behind:
        names = ", ".join(b["point_name"] for b in behind)
        parts.append(f"Проигрываем конкурентам: {names}.")
        # Самая частая «зона роста» среди отстающих.
        opp: dict = {}
        for b in behind:
            for o in b["opportunities"]:
                opp[o] = opp.get(o, 0) + 1
        if opp:
            top = sorted(opp.items(), key=lambda kv: -kv[1])[0][0]
            parts.append(f"Чаще всего соседи сильнее в: «{top}» — это приоритет.")
    if leading:
        parts.append(f"Лидируем в районе: {', '.join(b['point_name'] for b in leading)}.")
    if not parts:
        parts.append("Сравнение собрано — смотрите детали по точкам ниже.")
    return " ".join(parts)
