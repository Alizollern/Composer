"""action_items (M9 — отслеживание исправлений: нашли → поручили → проверили)

Revision ID: c3e5f7b9d1a4
Revises: b2d4f6a8c0e2
Create Date: 2026-06-14 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3e5f7b9d1a4'
down_revision: Union[str, None] = 'b2d4f6a8c0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'action_items',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('company_id', sa.String(length=32), nullable=False),
        sa.Column('point_id', sa.String(length=32), nullable=True),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('detail', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='open'),
        sa.Column('source', sa.String(length=16), nullable=False, server_default='manual'),
        sa.Column('created_by', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_action_items_company_id'), 'action_items',
                    ['company_id'], unique=False)
    op.create_index(op.f('ix_action_items_point_id'), 'action_items',
                    ['point_id'], unique=False)
    op.create_index(op.f('ix_action_items_status'), 'action_items',
                    ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_action_items_status'), table_name='action_items')
    op.drop_index(op.f('ix_action_items_point_id'), table_name='action_items')
    op.drop_index(op.f('ix_action_items_company_id'), table_name='action_items')
    op.drop_table('action_items')
