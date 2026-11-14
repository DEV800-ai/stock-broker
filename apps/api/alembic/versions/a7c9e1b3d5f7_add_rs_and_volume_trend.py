"""add_rs_and_volume_trend

Stored stats behind the v2 composite (3m/6m relative strength vs sector ETF,
20d/60d volume trend).

Revision ID: a7c9e1b3d5f7
Revises: f6a8c0e2b4d6
Create Date: 2026-11-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c9e1b3d5f7'
down_revision: Union[str, None] = 'f6a8c0e2b4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('scan_results', sa.Column('volume_trend_ratio', sa.Double(), nullable=True))
    op.add_column('scan_results', sa.Column('rs_excess_3m', sa.Double(), nullable=True))
    op.add_column('scan_results', sa.Column('rs_excess_6m', sa.Double(), nullable=True))


def downgrade() -> None:
    op.drop_column('scan_results', 'rs_excess_6m')
    op.drop_column('scan_results', 'rs_excess_3m')
    op.drop_column('scan_results', 'volume_trend_ratio')
