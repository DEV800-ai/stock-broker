"""add_fill_realism_columns

Revision ID: a3c7e1f2b4d6
Revises: f4a1b6c9d0e2
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c7e1f2b4d6'
down_revision: Union[str, None] = 'f4a1b6c9d0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('paper_trades', sa.Column('requested_shares', sa.Integer(), nullable=True))
    op.add_column('paper_trades', sa.Column('theoretical_entry_price', sa.Double(), nullable=True))
    op.add_column('paper_trades', sa.Column('theoretical_exit_price', sa.Double(), nullable=True))
    op.add_column('paper_trades', sa.Column('fill_status', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('paper_trades', 'fill_status')
    op.drop_column('paper_trades', 'theoretical_exit_price')
    op.drop_column('paper_trades', 'theoretical_entry_price')
    op.drop_column('paper_trades', 'requested_shares')
