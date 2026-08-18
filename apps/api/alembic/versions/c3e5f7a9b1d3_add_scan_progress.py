"""add_scan_progress

Revision ID: c3e5f7a9b1d3
Revises: b2d4f6a8c0e2
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3e5f7a9b1d3'
down_revision: Union[str, None] = 'b2d4f6a8c0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('scan_runs', sa.Column('phase', sa.String(length=20), nullable=True))
    op.add_column('scan_runs', sa.Column('total_tickers', sa.Integer(), nullable=True))
    op.add_column('scan_runs', sa.Column('tickers_processed', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('scan_runs', 'tickers_processed')
    op.drop_column('scan_runs', 'total_tickers')
    op.drop_column('scan_runs', 'phase')
