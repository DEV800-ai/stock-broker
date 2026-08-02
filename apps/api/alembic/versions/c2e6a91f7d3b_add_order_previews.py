"""add_order_previews

Revision ID: c2e6a91f7d3b
Revises: 8aff0d334b6a
Create Date: 2026-08-02 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2e6a91f7d3b'
down_revision: Union[str, None] = '8aff0d334b6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('order_previews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticker', sa.String(length=12), nullable=False),
    sa.Column('thesis_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=10), nullable=False),
    sa.Column('shares', sa.Integer(), nullable=False),
    sa.Column('order_type', sa.String(length=20), nullable=False),
    sa.Column('limit_price', sa.Double(), nullable=False),
    sa.Column('time_in_force', sa.String(length=10), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('bull_case', sa.Text(), nullable=True),
    sa.Column('bear_case', sa.Text(), nullable=True),
    sa.Column('portfolio_impact', sa.Text(), nullable=True),
    sa.Column('risk_status', sa.String(length=30), nullable=False),
    sa.Column('approval_required', sa.Boolean(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('paper_trade_id', sa.Integer(), nullable=True),
    sa.Column('approved_by', sa.String(length=100), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['thesis_id'], ['stock_theses.id'], ),
    sa.ForeignKeyConstraint(['paper_trade_id'], ['paper_trades.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_previews_ticker'), 'order_previews', ['ticker'], unique=False)
    op.create_index(op.f('ix_order_previews_status'), 'order_previews', ['status'], unique=False)

    op.create_foreign_key(
        'fk_risk_evaluations_order_preview_id', 'risk_evaluations', 'order_previews',
        ['order_preview_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_risk_evaluations_order_preview_id', 'risk_evaluations', type_='foreignkey')
    op.drop_index(op.f('ix_order_previews_status'), table_name='order_previews')
    op.drop_index(op.f('ix_order_previews_ticker'), table_name='order_previews')
    op.drop_table('order_previews')
