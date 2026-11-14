"""add_atr_and_preview_levels

ATR(14) on scan_results, and the descriptive ATR stop / reference target /
risk-based size on order_previews.

Revision ID: c9e1a3b5d7f9
Revises: b8d0f2a4c6e8
Create Date: 2026-11-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9e1a3b5d7f9'
down_revision: Union[str, None] = 'b8d0f2a4c6e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('scan_results', sa.Column('atr_14', sa.Double(), nullable=True))
    op.add_column('order_previews', sa.Column('atr_14', sa.Double(), nullable=True))
    op.add_column('order_previews', sa.Column('stop_price', sa.Double(), nullable=True))
    op.add_column('order_previews', sa.Column('reference_target', sa.Double(), nullable=True))
    op.add_column('order_previews', sa.Column('risk_sized_shares', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('order_previews', 'risk_sized_shares')
    op.drop_column('order_previews', 'reference_target')
    op.drop_column('order_previews', 'stop_price')
    op.drop_column('order_previews', 'atr_14')
    op.drop_column('scan_results', 'atr_14')
