"""add_manual_execution_tracking

Revision ID: b3d5f7a9c1e3
Revises: a9c2e4f6b8d0
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3d5f7a9c1e3'
down_revision: Union[str, None] = 'a9c2e4f6b8d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'paper_trades',
        sa.Column('source', sa.String(length=20), nullable=False, server_default='paper'),
    )
    op.alter_column('paper_trades', 'source', server_default=None)
    op.add_column('paper_trades', sa.Column('reported_by', sa.String(length=100), nullable=True))
    op.add_column('paper_trades', sa.Column('execution_notes', sa.Text(), nullable=True))
    # executed|executed_with_changes|rejected|watch_only|paper_tracked|cancelled — only
    # populated for source="manual_tradingview" rows; NULL for ordinary simulated paper trades.
    op.add_column('paper_trades', sa.Column('outcome', sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column('paper_trades', 'outcome')
    op.drop_column('paper_trades', 'execution_notes')
    op.drop_column('paper_trades', 'reported_by')
    op.drop_column('paper_trades', 'source')
