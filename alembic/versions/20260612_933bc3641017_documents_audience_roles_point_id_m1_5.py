"""documents: audience_roles + point_id (M1.5)

Revision ID: 933bc3641017
Revises: f58fea393fec
Create Date: 2026-06-12 15:10:24.133792+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '933bc3641017'
down_revision: Union[str, None] = 'f58fea393fec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default='[]' — безопасно для таблицы с существующими строками
    # (старые документы получают пустую аудиторию = видны всем).
    op.add_column('documents', sa.Column(
        'audience_roles', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('documents', sa.Column('point_id', sa.String(length=32), nullable=True))
    op.create_index(op.f('ix_documents_point_id'), 'documents', ['point_id'], unique=False)
    # FK добавляем только на Postgres: на SQLite ALTER ADD CONSTRAINT не
    # поддерживается, а там схему всё равно ведёт create_all (FK уже в модели).
    if op.get_bind().dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_documents_point_id", "documents", "points",
            ["point_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("fk_documents_point_id", "documents", type_="foreignkey")
    op.drop_index(op.f('ix_documents_point_id'), table_name='documents')
    op.drop_column('documents', 'point_id')
    op.drop_column('documents', 'audience_roles')
