"""add_elliott_wave_context

Revision ID: f6a8c0e2b4d6
Revises: d4f6a8c0e2b3
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a8c0e2b4d6'
down_revision: Union[str, None] = 'd4f6a8c0e2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stock_theses', sa.Column('elliott_wave_context', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('stock_theses', 'elliott_wave_context')
