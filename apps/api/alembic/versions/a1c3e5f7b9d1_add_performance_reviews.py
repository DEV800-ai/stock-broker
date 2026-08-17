"""add_performance_reviews

Revision ID: a1c3e5f7b9d1
Revises: d8f1b3c5e7a9
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a1c3e5f7b9d1'
down_revision: Union[str, None] = 'd8f1b3c5e7a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'performance_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('triggered_by', sa.String(length=20), nullable=False),
        sa.Column('report_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_performance_reviews_period_start'), 'performance_reviews', ['period_start'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_performance_reviews_period_start'), table_name='performance_reviews')
    op.drop_table('performance_reviews')
