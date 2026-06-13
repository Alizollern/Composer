"""M4 — «Цифровой операционный директор»: отзывы клиентов → инсайты собственнику.

Петля:
  1) sync_reviews  — тянем отзывы точки из источника (2GIS), без дублей;
  2) analyze_pending — AI читает каждый отзыв: тональность, тема, жалоба ли,
     и (через RAG по стандартам) какой регламент она задевает + рекомендация;
  3) command_center — собираем экран собственника: пульс точки, главные боли
     (жалобы, сгруппированные и привязанные к стандартам), лента отзывов.

Строгий контракт разбора (как в чате/тесте): модель зовётся через brain.complete
и обязана вернуть валидный JSON. Падение модели не роняет синхронизацию —
тональность тогда выводится из оценки (rating), а жалоба = низкая оценка.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from product import brain
from product.agent_log import log_event
from product.db import models as m
from product.rag import get_embedder, search_chunks
from product.rag.embedder import Embedder
from product.reviews import get_review_source, parse_2gis_id
from product.reviews.source import ReviewSource

# Отзывы неформальные и короткие — порог привязки к стандарту ниже, чем в чате.
REVIEW_MATCH_MIN = 0.18

_ANALYZE_SYSTEM = (
    "Ты — операционный директор сети. Тебе дают отзыв клиента о точке и, возможно, "
    "релевантный фрагмент внутреннего стандарта компании. Оцени отзыв.\n"
    "Верни РОВНО валидный JSON-объект без markdown и без пояснений:\n"
    '{"sentiment": "positive|neutral|negative", "topic": "тема 1-3 слова", '
    '"is_complaint": true|false, "recommendation": "что сделать управляющему, 1 фраза"}\n'
    "- sentiment — общая тональность отзыва;\n"
    "- topic — короткая тема (напр. «Чистота», «Обслуживание», «Оборудование»);\n"
    "- is_complaint — true, если клиент на что-то жалуется и это операционная проблема;\n"
    "- recommendation — конкретное действие управляющему (пусто, если жалобы нет).\n"
    "Опирайся на текст отзыва; стандарт — лишь чтобы понять, какой регламент задет."
)


class ReviewError(Exception):
    """Проблема при работе с отзывами (некорректная ссылка и т.п.)."""


# --------------------------- Точки и синхронизация ---------------------------

def connect_point(db: Session, company_id: str, *, name: str, url: str,
                  source: str = m.REVIEW_2GIS) -> m.Point:
    """Подключить точку к источнику отзывов (по ссылке 2GIS)."""
    name = (name or "").strip() or "Точка"
    external_id = parse_2gis_id(url)  # бросит ValueError при кривой ссылке
    point = m.Point(company_id=company_id, name=name, source=source,
                    external_id=external_id, external_url=url.strip())
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


def list_points(db: Session, company_id: str) -> List[m.Point]:
    stmt = (select(m.Point).where(m.Point.company_id == company_id)
            .order_by(m.Point.created_at.asc()))
    return list(db.execute(stmt).scalars().all())


def get_point(db: Session, company_id: str, point_id: str) -> m.Point:
    point = db.get(m.Point, point_id)
    if point is None or point.company_id != company_id:
        raise KeyError("Точка не найдена")
    return point


def sync_reviews(db: Session, company_id: str, point_id: str, *,
                 source: Optional[ReviewSource] = None, limit: int = 50) -> int:
    """Подтянуть новые отзывы точки из источника. Возвращает число новых."""
    point = get_point(db, company_id, point_id)
    src = source or get_review_source()
    raws = src.fetch(point.external_id or point.external_url, limit=limit)

    # Что уже есть (по external_id в рамках компании+источника) — чтобы не дублить.
    existing = set(db.execute(
        select(m.Review.external_id).where(
            m.Review.company_id == company_id,
            m.Review.source == src.name,
        )).scalars().all())

    added = 0
    for r in raws:
        eid = (r.external_id or "").strip()
        if eid and eid in existing:
            continue
        db.add(m.Review(
            company_id=company_id, point_id=point.id, source=src.name,
            external_id=eid, author=r.author, rating=r.rating or 0,
            text=r.text, dated_at=r.dated_at))
        if eid:
            existing.add(eid)
        added += 1
    db.commit()
    log_event("reviews.sync", company=company_id, point=point.id,
              source=src.name, fetched=len(raws), added=added)
    return added


# ------------------------------- AI-разбор -----------------------------------

def _parse_obj(raw: str) -> dict:
    """Достать JSON-объект из ответа модели (терпим к ```-обёрткам/префиксам)."""
    text = (raw or "").strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j != -1 and j > i:
            text = text[i:j + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("ожидался JSON-объект")
    return data


def _sentiment_from_rating(rating: int) -> str:
    if rating >= 4:
        return m.SENTIMENT_POSITIVE
    if rating == 3:
        return m.SENTIMENT_NEUTRAL
    return m.SENTIMENT_NEGATIVE  # 1-2 (и 0/неизвестно трактуем осторожно ниже)


def analyze_review(text: str, rating: int, *, standard_title: str = "",
                   standard_text: str = "", llm=None,
                   company: Optional[str] = None) -> dict:
    """Разобрать один отзыв. Возвращает {sentiment, topic, is_complaint, recommendation}.

    На сбое модели — безопасный откат к оценке: тональность и факт жалобы по rating.
    """
    fallback = {
        "sentiment": _sentiment_from_rating(rating) if rating else m.SENTIMENT_NEUTRAL,
        "topic": "",
        "is_complaint": bool(rating and rating <= 2),
        "recommendation": "",
    }
    if not text.strip():
        return fallback
    ctx = ""
    if standard_text:
        ctx = (f"\n\n=== РЕЛЕВАНТНЫЙ СТАНДАРТ: «{standard_title}» ===\n"
               f"{standard_text}")
    user = (f"Оценка клиента: {rating or '—'} из 5.\n"
            f"Текст отзыва:\n{text}{ctx}")
    try:
        raw = brain.complete(_ANALYZE_SYSTEM, user, llm=llm,
                             operation="review_analyze", company=company)
        data = _parse_obj(raw)
    except Exception:
        return fallback
    sentiment = str(data.get("sentiment", "")).strip().lower()
    if sentiment not in (m.SENTIMENT_POSITIVE, m.SENTIMENT_NEUTRAL, m.SENTIMENT_NEGATIVE):
        sentiment = fallback["sentiment"]
    return {
        "sentiment": sentiment,
        "topic": str(data.get("topic", "")).strip()[:255],
        "is_complaint": bool(data.get("is_complaint", fallback["is_complaint"])),
        "recommendation": str(data.get("recommendation", "")).strip(),
    }


def analyze_pending(db: Session, company_id: str, *, point_id: Optional[str] = None,
                    embedder: Optional[Embedder] = None, llm=None,
                    limit: int = 300) -> int:
    """Разобрать ещё не проанализированные отзывы. Возвращает число разобранных.

    Позитивные отзывы (rating>=4) не гоняем через модель — экономим вызовы:
    тональность ясна, жалобы нет. Остальные разбираем и привязываем к стандарту
    через RAG (косинус по тексту отзыва).
    """
    stmt = select(m.Review).where(
        m.Review.company_id == company_id, m.Review.analyzed.is_(False))
    if point_id:
        stmt = stmt.where(m.Review.point_id == point_id)
    stmt = stmt.order_by(m.Review.dated_at.desc().nullslast()).limit(limit)
    pending = list(db.execute(stmt).scalars().all())
    if not pending:
        return 0

    embedder = embedder or get_embedder()
    done = 0
    for rv in pending:
        # Похвала: размечаем дёшево, без модели и без привязки к стандарту.
        if rv.rating and rv.rating >= 4:
            rv.sentiment = m.SENTIMENT_POSITIVE
            rv.topic = "Похвала"
            rv.is_complaint = False
            rv.recommendation = ""
            rv.matched_document_id = None
            rv.matched_document_title = ""
            rv.matched_quote = ""
            rv.analyzed = True
            done += 1
            continue

        # Ищем релевантный стандарт по тексту отзыва.
        best = None
        try:
            q_vec = embedder.embed_one(rv.text)
            hits = search_chunks(db, company_id, q_vec, top_k=1)
            if hits and hits[0].score >= REVIEW_MATCH_MIN:
                best = hits[0]
        except Exception:
            best = None

        res = analyze_review(
            rv.text, rv.rating,
            standard_title=best.document_title if best else "",
            standard_text=best.text if best else "",
            llm=llm, company=company_id)

        rv.sentiment = res["sentiment"]
        rv.topic = res["topic"]
        rv.is_complaint = res["is_complaint"]
        rv.recommendation = res["recommendation"]
        if res["is_complaint"] and best:
            rv.matched_document_id = best.document_id
            rv.matched_document_title = best.document_title
            rv.matched_quote = best.text[:400]
        else:
            rv.matched_document_id = None
            rv.matched_document_title = ""
            rv.matched_quote = ""
        rv.analyzed = True
        done += 1

    db.commit()
    log_event("reviews.analyze", company=company_id, point=point_id, analyzed=done)
    return done


def sync_and_analyze(db: Session, company_id: str, point_id: str, *,
                     source: Optional[ReviewSource] = None,
                     embedder: Optional[Embedder] = None, llm=None,
                     limit: int = 50) -> dict:
    """Кнопка «Обновить отзывы»: подтянуть + сразу разобрать новые."""
    added = sync_reviews(db, company_id, point_id, source=source, limit=limit)
    analyzed = analyze_pending(db, company_id, point_id=point_id,
                               embedder=embedder, llm=llm)
    return {"added": added, "analyzed": analyzed}


# ----------------------------- Командный центр -------------------------------

def _reviews_for(db: Session, company_id: str, point_id: Optional[str]) -> List[m.Review]:
    stmt = select(m.Review).where(m.Review.company_id == company_id)
    if point_id:
        stmt = stmt.where(m.Review.point_id == point_id)
    stmt = stmt.order_by(m.Review.dated_at.desc().nullslast(),
                         m.Review.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def _snippet(text: str, n: int = 160) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n].rstrip() + "…"


def command_center(db: Session, company_id: str, *, point_id: Optional[str] = None,
                   limit_recent: int = 30) -> dict:
    """Собрать экран собственника: пульс + главные боли + лента отзывов."""
    points = list_points(db, company_id)
    # Сводка по каждой точке (для переключателя в UI).
    counts = defaultdict(lambda: {"total": 0, "negative": 0})
    for rv in _reviews_for(db, company_id, None):
        c = counts[rv.point_id]
        c["total"] += 1
        if rv.sentiment == m.SENTIMENT_NEGATIVE:
            c["negative"] += 1
    points_out = [{
        "id": p.id, "name": p.name, "source": p.source,
        "external_url": p.external_url,
        "reviews_count": counts[p.id]["total"],
        "negative_count": counts[p.id]["negative"],
    } for p in points]

    reviews = _reviews_for(db, company_id, point_id)

    # --- Пульс ---
    rated = [r.rating for r in reviews if r.rating]
    pulse = {
        "total": len(reviews),
        "analyzed": sum(1 for r in reviews if r.analyzed),
        "avg_rating": round(sum(rated) / len(rated), 2) if rated else 0.0,
        "positive": sum(1 for r in reviews if r.sentiment == m.SENTIMENT_POSITIVE),
        "neutral": sum(1 for r in reviews if r.sentiment == m.SENTIMENT_NEUTRAL),
        "negative": sum(1 for r in reviews if r.sentiment == m.SENTIMENT_NEGATIVE),
        "complaints": sum(1 for r in reviews if r.is_complaint),
    }

    # --- Главные боли: группируем жалобы по стандарту (или по теме) ---
    groups: dict = {}
    for r in reviews:
        if not r.is_complaint:
            continue
        key = r.matched_document_id or f"topic:{(r.topic or 'Прочее').lower()}"
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                "key": key,
                "title": r.matched_document_title or (r.topic or "Прочее"),
                "document_id": r.matched_document_id,
                "standard_quote": r.matched_quote or "",
                "count": 0,
                "recommendation": "",
                "samples": [],
            }
        g["count"] += 1
        if not g["recommendation"] and r.recommendation:
            g["recommendation"] = r.recommendation
        if not g["standard_quote"] and r.matched_quote:
            g["standard_quote"] = r.matched_quote
        if len(g["samples"]) < 3:
            g["samples"].append(_snippet(r.text))
    problems = sorted(groups.values(), key=lambda g: g["count"], reverse=True)

    # --- Лента последних отзывов ---
    recent = [{
        "id": r.id,
        "author": r.author,
        "rating": r.rating,
        "text": r.text,
        "dated_at": r.dated_at.isoformat() if r.dated_at else None,
        "sentiment": r.sentiment,
        "topic": r.topic,
        "is_complaint": r.is_complaint,
        "matched_document_title": r.matched_document_title,
        "recommendation": r.recommendation,
    } for r in reviews[:limit_recent]]

    return {
        "points": points_out,
        "selected_point_id": point_id,
        "pulse": pulse,
        "problems": problems,
        "recent": recent,
    }
