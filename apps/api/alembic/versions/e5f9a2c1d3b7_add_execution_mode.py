"""add_execution_mode

Revision ID: e5f9a2c1d3b7
Revises: a3c7e1f2b4d6
Create Date: 2026-08-09 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f9a2c1d3b7'
down_revision: Union[str, None] = 'a3c7e1f2b4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'order_previews',
        sa.Column('execution_mode', sa.String(length=20), nullable=False, server_default='paper'),
    )
    op.alter_column('order_previews', 'execution_mode', server_default=None)


def downgrade() -> None:
    op.drop_column('order_previews', 'execution_mode')
