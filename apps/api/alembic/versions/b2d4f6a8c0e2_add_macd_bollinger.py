"""add_macd_bollinger

Revision ID: b2d4f6a8c0e2
Revises: a1c3e5f7b9d1
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d4f6a8c0e2'
down_revision: Union[str, None] = 'a1c3e5f7b9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('scan_results', sa.Column('macd', sa.Double(), nullable=True))
    op.add_column('scan_results', sa.Column('macd_signal', sa.Double(), nullable=True))
    op.add_column('scan_results', sa.Column('macd_histogram', sa.Double(), nullable=True))
    op.add_column('scan_results', sa.Column('bb_upper', sa.Double(), nullable=True))
    op.add_column('scan_results', sa.Column('bb_lower', sa.Double(), nullable=True))
    op.add_column('scan_results', sa.Column('bb_percent_b', sa.Double(), nullable=True))


def downgrade() -> None:
    op.drop_column('scan_results', 'bb_percent_b')
    op.drop_column('scan_results', 'bb_lower')
    op.drop_column('scan_results', 'bb_upper')
    op.drop_column('scan_results', 'macd_histogram')
    op.drop_column('scan_results', 'macd_signal')
    op.drop_column('scan_results', 'macd')
