"""phase-80 step-1: reward_campaigns + reward_campaign_uses

Revision ID: d3e4f5a6b7c8
Revises: c2b3d4e5f6a7
Create Date: 2026-10-04 18:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2b3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reward_campaigns',
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('conditions', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('reward_type', sa.String(length=30), nullable=False),
        sa.Column('reward_value', sa.Numeric(12, 2), nullable=False),
        sa.Column('funding_source', sa.String(length=20), nullable=False, server_default='CAMPAIGN'),
        sa.Column('budget_total', sa.Numeric(12, 2), nullable=True),
        sa.Column('budget_used', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('usage_limit', sa.Integer(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_limit', sa.Integer(), nullable=True),
        sa.Column('economic_cap_pct', sa.Numeric(6, 4), nullable=False, server_default='0.5'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_reward_campaigns_active_dates', 'reward_campaigns',
        ['active', 'start_at', 'end_at'], unique=False,
    )
    op.create_index(
        'ix_reward_campaigns_tenant', 'reward_campaigns', ['tenant_id'], unique=False,
    )

    op.create_table(
        'reward_campaign_uses',
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('campaign_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('booking_id', sa.String(length=36), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='AED'),
        sa.Column('ledger_reward_id', sa.String(length=36), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['reward_campaigns.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['ledger_reward_id'], ['rewards.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_reward_campaign_uses_campaign', 'reward_campaign_uses',
        ['campaign_id', 'used_at'], unique=False,
    )
    op.create_index(
        'ix_reward_campaign_uses_user', 'reward_campaign_uses',
        ['user_id', 'campaign_id'], unique=False,
    )
    op.create_index(
        'ix_reward_campaign_uses_booking', 'reward_campaign_uses',
        ['booking_id'], unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_reward_campaign_uses_booking', table_name='reward_campaign_uses')
    op.drop_index('ix_reward_campaign_uses_user', table_name='reward_campaign_uses')
    op.drop_index('ix_reward_campaign_uses_campaign', table_name='reward_campaign_uses')
    op.drop_table('reward_campaign_uses')
    op.drop_index('ix_reward_campaigns_tenant', table_name='reward_campaigns')
    op.drop_index('ix_reward_campaigns_active_dates', table_name='reward_campaigns')
    op.drop_table('reward_campaigns')
