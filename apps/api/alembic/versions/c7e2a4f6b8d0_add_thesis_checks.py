"""add_thesis_checks

Revision ID: c7e2a4f6b8d0
Revises: b3d5f7a9c1e3
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7e2a4f6b8d0'
down_revision: Union[str, None] = 'b3d5f7a9c1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('thesis_checks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticker', sa.String(length=12), nullable=False),
    sa.Column('thesis_id', sa.Integer(), nullable=False),
    sa.Column('new_thesis_id', sa.Integer(), nullable=True),
    sa.Column('triggered_by', sa.String(length=20), nullable=False),
    sa.Column('checked_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('changed', sa.Boolean(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['thesis_id'], ['stock_theses.id'], ),
    sa.ForeignKeyConstraint(['new_thesis_id'], ['stock_theses.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_thesis_checks_ticker'), 'thesis_checks', ['ticker'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_thesis_checks_ticker'), table_name='thesis_checks')
    op.drop_table('thesis_checks')
