"""drop_ibkr_conid

Revision ID: d8f1b3c5e7a9
Revises: c7e2a4f6b8d0
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8f1b3c5e7a9'
down_revision: Union[str, None] = 'c7e2a4f6b8d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('stock_universe', 'ibkr_conid')


def downgrade() -> None:
    op.add_column('stock_universe', sa.Column('ibkr_conid', sa.Integer(), nullable=True))
