"""drop_elliott_wave_context

The thesis model only sees a few summary numbers, never the chart, so an
Elliott Wave read is not defensible output. Reverses f6a8c0e2b4d6.

Revision ID: b8d0f2a4c6e8
Revises: a7c9e1b3d5f7
Create Date: 2026-11-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8d0f2a4c6e8'
down_revision: Union[str, None] = 'a7c9e1b3d5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('stock_theses', 'elliott_wave_context')


def downgrade() -> None:
    op.add_column('stock_theses', sa.Column('elliott_wave_context', sa.Text(), nullable=True))
