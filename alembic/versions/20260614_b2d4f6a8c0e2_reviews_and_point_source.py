"""reviews + point source fields (M4 — цифровой опер-дир: анализ отзывов 2GIS)

Revision ID: b2d4f6a8c0e2
Revises: a1c2e3f4d5b6
Create Date: 2026-06-14 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d4f6a8c0e2'
down_revision: Union[str, None] = 'a1c2e3f4d5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Точка получает привязку к внешнему источнику отзывов.
    op.add_column('points', sa.Column('source', sa.String(length=32),
                                      nullable=False, server_default=''))
    op.add_column('points', sa.Column('external_id', sa.String(length=128),
                                      nullable=False, server_default=''))
    op.add_column('points', sa.Column('external_url', sa.String(length=1024),
                                      nullable=False, server_default=''))
    op.create_index(op.f('ix_points_external_id'), 'points', ['external_id'],
                    unique=False)

    # Отзывы клиентов + результат AI-разбора.
    op.create_table(
        'reviews',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('company_id', sa.String(length=32), nullable=False),
        sa.Column('point_id', sa.String(length=32), nullable=True),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('external_id', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('author', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('rating', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text', sa.Text(), nullable=False, server_default=''),
        sa.Column('dated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analyzed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('sentiment', sa.String(length=16), nullable=False, server_default=''),
        sa.Column('topic', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('is_complaint', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('matched_document_id', sa.String(length=32), nullable=True),
        sa.Column('matched_document_title', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('matched_quote', sa.Text(), nullable=False, server_default=''),
        sa.Column('recommendation', sa.Text(), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['matched_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'source', 'external_id',
                            name='uq_review_company_source_ext'),
    )
    op.create_index(op.f('ix_reviews_company_id'), 'reviews', ['company_id'], unique=False)
    op.create_index(op.f('ix_reviews_point_id'), 'reviews', ['point_id'], unique=False)
    op.create_index(op.f('ix_reviews_analyzed'), 'reviews', ['analyzed'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reviews_analyzed'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_point_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_company_id'), table_name='reviews')
    op.drop_table('reviews')
    op.drop_index(op.f('ix_points_external_id'), table_name='points')
    op.drop_column('points', 'external_url')
    op.drop_column('points', 'external_id')
    op.drop_column('points', 'source')
