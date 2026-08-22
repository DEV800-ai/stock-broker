"""add_tracked_tickers

Revision ID: d4f6a8c0e2b3
Revises: c3e5f7a9b1d3
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f6a8c0e2b3'
down_revision: Union[str, None] = 'c3e5f7a9b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tracked_tickers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('ticker', sa.String(length=12), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('actor', 'ticker', name='uq_tracked_ticker_actor_ticker'),
    )
    op.create_index('ix_tracked_tickers_actor', 'tracked_tickers', ['actor'])


def downgrade() -> None:
    op.drop_index('ix_tracked_tickers_actor', table_name='tracked_tickers')
    op.drop_table('tracked_tickers')
