"""
Поиск по чанкам компании (косинусная близость).

Сейчас — простой и честный baseline: тянем чанки тенанта, считаем косинус в
Python, берём top-k. Это шов: когда объёмы вырастут, тут же подменяется на
pgvector + ANN-индекс, не трогая вызывающий код (модули M1/M2) и схему БД.

Изоляция тенанта — обязательна: выборка всегда фильтруется по company_id.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from product.db import models as m


def cosine(a: List[float], b: List[float]) -> float:
    """Косинусная близость двух векторов. 0.0, если длины не совпали или нули."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass
class SearchHit:
    """Найденный чанк с оценкой близости и данными для цитирования."""
    chunk_id: str
    document_id: str
    version_id: str
    document_title: str
    ordinal: int
    text: str
    score: float


def search_chunks(
    db: Session,
    company_id: str,
    query_embedding: List[float],
    *,
    top_k: int = 5,
    only_published: bool = True,
    allowed_document_ids: Optional[set] = None,
) -> List[SearchHit]:
    """Найти top_k самых близких чанков компании к вектору запроса.

    only_published — искать лишь по опубликованным документам (то, что реально
    действует как стандарт). Чанки версий-черновиков в выдачу не попадают.

    allowed_document_ids — если задано, поиск ограничен этими документами (M1.5:
    аудитория стандарта для сотрудника). None = без ограничения (управляющий/owner).
    Пустое множество = виден ноль документов → пустая выдача.

    На Postgres сначала пробуем pgvector (ANN-индекс); если путь недоступен
    (SQLite, флаг выключен, размерность не совпала) — честно считаем косинус в
    Python. Контракт (SearchHit, сортировка по убыванию score) одинаков.
    """
    if allowed_document_ids is not None and not allowed_document_ids:
        return []

    from product.rag import pgvector_index
    hits = pgvector_index.search(
        db, company_id, query_embedding, top_k=top_k,
        only_published=only_published, allowed_document_ids=allowed_document_ids)
    if hits is not None:
        return hits

    stmt = (
        select(m.Chunk, m.Document.title, m.Document.status)
        .join(m.Document, m.Chunk.document_id == m.Document.id)
        .where(m.Chunk.company_id == company_id)
    )
    if only_published:
        stmt = stmt.where(m.Document.status == m.DOC_PUBLISHED)
    if allowed_document_ids is not None:
        stmt = stmt.where(m.Chunk.document_id.in_(allowed_document_ids))

    hits: List[SearchHit] = []
    for chunk, title, _status in db.execute(stmt).all():
        score = cosine(query_embedding, chunk.embedding or [])
        hits.append(SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            version_id=chunk.version_id,
            document_title=title,
            ordinal=chunk.ordinal,
            text=chunk.text,
            score=score,
        ))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]
