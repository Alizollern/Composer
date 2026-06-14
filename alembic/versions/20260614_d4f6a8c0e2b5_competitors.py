"""competitors (конкурентная разведка опер-дира: кто рядом, чем лучше)

Revision ID: d4f6a8c0e2b5
Revises: c3e5f7b9d1a4
Create Date: 2026-06-14 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f6a8c0e2b5'
down_revision: Union[str, None] = 'c3e5f7b9d1a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'competitors',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('company_id', sa.String(length=32), nullable=False),
        sa.Column('point_id', sa.String(length=32), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False, server_default='2gis'),
        sa.Column('external_id', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('distance_m', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating', sa.Float(), nullable=False, server_default='0'),
        sa.Column('reviews_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('weaknesses', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'point_id', 'external_id',
                            name='uq_competitor_company_point_ext'),
    )
    op.create_index(op.f('ix_competitors_company_id'), 'competitors',
                    ['company_id'], unique=False)
    op.create_index(op.f('ix_competitors_point_id'), 'competitors',
                    ['point_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_competitors_point_id'), table_name='competitors')
    op.drop_index(op.f('ix_competitors_company_id'), table_name='competitors')
    op.drop_table('competitors')
