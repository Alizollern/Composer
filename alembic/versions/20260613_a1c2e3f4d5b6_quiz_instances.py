"""quiz_instances: серверное хранение сгенерированных тестов

Revision ID: a1c2e3f4d5b6
Revises: 933bc3641017
Create Date: 2026-06-13 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c2e3f4d5b6'
down_revision: Union[str, None] = '933bc3641017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('quiz_instances',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=False),
    sa.Column('document_id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=True),
    sa.Column('questions', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_instances_company_id'), 'quiz_instances', ['company_id'], unique=False)
    op.create_index(op.f('ix_quiz_instances_document_id'), 'quiz_instances', ['document_id'], unique=False)
    op.create_index(op.f('ix_quiz_instances_user_id'), 'quiz_instances', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_quiz_instances_user_id'), table_name='quiz_instances')
    op.drop_index(op.f('ix_quiz_instances_document_id'), table_name='quiz_instances')
    op.drop_index(op.f('ix_quiz_instances_company_id'), table_name='quiz_instances')
    op.drop_table('quiz_instances')
