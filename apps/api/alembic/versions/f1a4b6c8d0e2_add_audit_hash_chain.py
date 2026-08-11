"""add_audit_hash_chain

Revision ID: f1a4b6c8d0e2
Revises: e5f9a2c1d3b7
Create Date: 2026-08-09 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a4b6c8d0e2'
down_revision: Union[str, None] = 'e5f9a2c1d3b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: rows written before this migration have no hash and sit outside the
    # chain; every row audit/service.py::log() writes from now on always sets both.
    op.add_column('audit_log', sa.Column('prev_hash', sa.String(length=64), nullable=True))
    op.add_column('audit_log', sa.Column('entry_hash', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('audit_log', 'entry_hash')
    op.drop_column('audit_log', 'prev_hash')
