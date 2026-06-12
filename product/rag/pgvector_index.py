"""
pgvector-ускорение поиска по чанкам (только Postgres).

Источник правды эмбеддингов — JSON-колонка chunks.embedding (переносимо между
SQLite и Postgres). Поверх неё на Postgres живёт колонка chunks.embedding_vec
типа vector(N) с HNSW-индексом по косинусу — её создаёт PG-only миграция.

Этот модуль:
  * sync_vectors() — после переиндексации заполняет embedding_vec для новых чанков;
  * search()       — ANN-поиск через оператор `<=>` (косинусная дистанция).

Всё построено как откатываемый шов: если путь недоступен (не Postgres, флаг
выключен, размерность вектора не совпала с колонкой) — функции возвращают None /
ничего не делают, и вызывающий код (rag.search) откатывается на Python-косинус.
Так система не ломается при смене модели эмбеддингов или на SQLite.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from product import config
from product.db import models as m


def is_postgres(db: Session) -> bool:
    bind = db.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _active(db: Session) -> bool:
    return config.PGVECTOR_ENABLED and is_postgres(db)


def _vec_literal(vec: Sequence[float]) -> str:
    """Текстовое представление вектора для каста `CAST(:v AS vector)`."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def sync_vectors(db: Session, rows: List[Tuple[str, List[float]]]) -> None:
    """Записать embedding_vec для чанков (id, embedding) на Postgres.

    Векторы неверной размерности пропускаются — для них embedding_vec останется
    NULL, и поиск по ним пойдёт через косинусный fallback."""
    if not _active(db):
        return
    dim = config.EMBEDDING_DIM
    stmt = text("UPDATE chunks SET embedding_vec = CAST(:v AS vector) WHERE id = :id")
    for chunk_id, vec in rows:
        if not vec or len(vec) != dim:
            continue
        db.execute(stmt, {"v": _vec_literal(vec), "id": chunk_id})


def search(
    db: Session,
    company_id: str,
    query_embedding: List[float],
    *,
    top_k: int = 5,
    only_published: bool = True,
    allowed_document_ids: Optional[set] = None,
):
    """ANN-поиск через pgvector. Возвращает list[SearchHit] либо None, если путь
    недоступен (тогда вызывающий код считает косинус в Python).

    allowed_document_ids — ограничить поиск этими документами (аудитория M1.5);
    None = без ограничения."""
    if not _active(db):
        return None
    if not query_embedding or len(query_embedding) != config.EMBEDDING_DIM:
        return None

    from product.rag.search import SearchHit  # отложенный импорт: избегаем цикла

    pub_clause = "AND d.status = :pub" if only_published else ""
    # = ANY(:ids) — портативный для psycopg способ передать список как массив.
    audience_clause = "AND c.document_id = ANY(:ids)" if allowed_document_ids is not None else ""
    sql = text(
        f"""
        SELECT c.id, c.document_id, c.version_id, d.title, c.ordinal, c.text,
               1 - (c.embedding_vec <=> CAST(:q AS vector)) AS score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.company_id = :cid AND c.embedding_vec IS NOT NULL {pub_clause} {audience_clause}
        ORDER BY c.embedding_vec <=> CAST(:q AS vector)
        LIMIT :k
        """
    )
    params = {"q": _vec_literal(query_embedding), "cid": company_id, "k": top_k}
    if only_published:
        params["pub"] = m.DOC_PUBLISHED
    if allowed_document_ids is not None:
        params["ids"] = list(allowed_document_ids)

    rows = db.execute(sql, params).all()
    return [
        SearchHit(
            chunk_id=r[0], document_id=r[1], version_id=r[2],
            document_title=r[3], ordinal=r[4], text=r[5], score=float(r[6]),
        )
        for r in rows
    ]
