"""add_risk_engine_tables

Revision ID: 8aff0d334b6a
Revises: 7f5abe150d86
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '8aff0d334b6a'
down_revision: Union[str, None] = '7f5abe150d86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('risk_policies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('rule_type', sa.String(length=50), nullable=False),
    sa.Column('params_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_policies_rule_type'), 'risk_policies', ['rule_type'], unique=False)

    op.create_table('risk_evaluations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticker', sa.String(length=12), nullable=False),
    sa.Column('order_preview_id', sa.Integer(), nullable=True),
    sa.Column('verdict', sa.String(length=30), nullable=False),
    sa.Column('rule_results_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_evaluations_ticker'), 'risk_evaluations', ['ticker'], unique=False)
    op.create_index(op.f('ix_risk_evaluations_order_preview_id'), 'risk_evaluations', ['order_preview_id'], unique=False)
    op.create_index(op.f('ix_risk_evaluations_verdict'), 'risk_evaluations', ['verdict'], unique=False)

    op.create_table('agent_control',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scope', sa.String(length=50), nullable=False),
    sa.Column('autonomy_mode', sa.String(length=30), nullable=False),
    sa.Column('is_killed', sa.Boolean(), nullable=True),
    sa.Column('killed_reason', sa.Text(), nullable=True),
    sa.Column('killed_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('agent_control')
    op.drop_index(op.f('ix_risk_evaluations_verdict'), table_name='risk_evaluations')
    op.drop_index(op.f('ix_risk_evaluations_order_preview_id'), table_name='risk_evaluations')
    op.drop_index(op.f('ix_risk_evaluations_ticker'), table_name='risk_evaluations')
    op.drop_table('risk_evaluations')
    op.drop_index(op.f('ix_risk_policies_rule_type'), table_name='risk_policies')
    op.drop_table('risk_policies')
