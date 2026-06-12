"""pgvector: chunks.embedding_vec + HNSW index (Postgres only)

Revision ID: 8a1f6e2c9d40
Revises: 4c97e17b5cff
Create Date: 2026-06-11 19:40:00.000000+00:00

Только для Postgres. На SQLite (офлайн/тесты) миграция — no-op: там pgvector нет,
а поиск идёт Python-косинусом по JSON-эмбеддингам. Размерность колонки берётся из
product.config.EMBEDDING_DIM (должна совпадать с моделью эмбеддингов).
"""
from typing import Sequence, Union

from alembic import op

from product.config import EMBEDDING_DIM

revision: str = '8a1f6e2c9d40'
down_revision: Union[str, None] = '4c97e17b5cff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_vec vector({EMBEDDING_DIM})")
    # HNSW по косинусной дистанции — быстрый ANN-поиск (оператор `<=>`).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_vec "
        "ON chunks USING hnsw (embedding_vec vector_cosine_ops)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_vec")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS embedding_vec")
