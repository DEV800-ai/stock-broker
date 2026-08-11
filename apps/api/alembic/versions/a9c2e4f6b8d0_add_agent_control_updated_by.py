"""add_agent_control_updated_by

Revision ID: a9c2e4f6b8d0
Revises: f1a4b6c8d0e2
Create Date: 2026-08-11 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a9c2e4f6b8d0'
down_revision: Union[str, None] = 'f1a4b6c8d0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agent_control', sa.Column('updated_by', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_control', 'updated_by')
