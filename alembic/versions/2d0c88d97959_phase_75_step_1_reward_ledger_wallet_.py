"""phase-75 step-1 reward ledger + wallet + rules

Revision ID: 2d0c88d97959
Revises: a6ca5215e333
Create Date: 2026-10-02 15:53:25.354694

Hand-written: removes the spurious `create_foreign_key` on tenants
(SQLite cannot ALTER constraints) and adds server-side defaults for
all new NOT NULL columns on `rewards` (SQLite requires this for
ALTER TABLE ADD COLUMN).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2d0c88d97959'
down_revision: Union[str, None] = 'a6ca5215e333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- reward_rules ---
    op.create_table(
        'reward_rules',
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('platform_reward_rate', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('max_reward_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('min_transaction_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category'),
    )
    op.create_index('ix_reward_rules_category_active', 'reward_rules',
                    ['category', 'enabled'], unique=False)

    # --- reward_wallets ---
    op.create_table(
        'reward_wallets',
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='AED'),
        sa.Column('available_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('locked_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('expiring_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('referral_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('experience_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('bonus_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('platform_cost_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('partner_cost_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('last_rebuilt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reward_wallets_tenant', 'reward_wallets', ['tenant_id'], unique=False)
    op.create_index('ix_reward_wallets_user', 'reward_wallets', ['user_id'], unique=True)

    # --- rewards: new columns (with server defaults for NOT NULL) ---
    op.add_column('rewards', sa.Column('source_type', sa.String(length=50), nullable=True))
    op.add_column('rewards', sa.Column('source_id', sa.String(length=36), nullable=True))
    op.add_column('rewards', sa.Column('amount', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('rewards', sa.Column('currency', sa.String(length=10), nullable=False, server_default='AED'))
    op.add_column('rewards', sa.Column('funding_source', sa.String(length=20), nullable=False, server_default='PLATFORM'))
    op.add_column('rewards', sa.Column('platform_cost', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('rewards', sa.Column('partner_contribution', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('rewards', sa.Column('status', sa.String(length=20), nullable=False, server_default='AVAILABLE'))
    op.add_column('rewards', sa.Column('available_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('rewards', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('rewards', sa.Column('transaction_id', sa.String(length=36), nullable=True))
    op.add_column('rewards', sa.Column('referral_id', sa.String(length=36), nullable=True))
    op.add_column('rewards', sa.Column('campaign_id', sa.String(length=36), nullable=True))
    op.add_column('rewards', sa.Column('extra', sa.JSON(), nullable=False, server_default='{}'))

    # NOTE: skipped ALTER COLUMN reward_type (SQLite does not support
    # ALTER COLUMN TYPE). VARCHAR(20) vs VARCHAR(50) is not enforced by
    # SQLite anyway; the model declares 50 for PostgreSQL.

    op.create_index('ix_rewards_expires_at', 'rewards', ['expires_at'], unique=False)
    op.create_index('ix_rewards_transaction', 'rewards', ['transaction_id'], unique=False)
    op.create_index('ix_rewards_user_status', 'rewards', ['user_id', 'status'], unique=False)
    # NOTE: skipped create_foreign_key on tenants (SQLite limitation).


def downgrade() -> None:
    op.drop_index('ix_rewards_user_status', table_name='rewards')
    op.drop_index('ix_rewards_transaction', table_name='rewards')
    op.drop_index('ix_rewards_expires_at', table_name='rewards')
    # NOTE: skipped (see upgrade).
    op.drop_column('rewards', 'extra')
    op.drop_column('rewards', 'campaign_id')
    op.drop_column('rewards', 'referral_id')
    op.drop_column('rewards', 'transaction_id')
    op.drop_column('rewards', 'expires_at')
    op.drop_column('rewards', 'available_at')
    op.drop_column('rewards', 'status')
    op.drop_column('rewards', 'partner_contribution')
    op.drop_column('rewards', 'platform_cost')
    op.drop_column('rewards', 'funding_source')
    op.drop_column('rewards', 'currency')
    op.drop_column('rewards', 'amount')
    op.drop_column('rewards', 'source_id')
    op.drop_column('rewards', 'source_type')
    op.drop_index('ix_reward_wallets_user', table_name='reward_wallets')
    op.drop_index('ix_reward_wallets_tenant', table_name='reward_wallets')
    op.drop_table('reward_wallets')
    op.drop_index('ix_reward_rules_category_active', table_name='reward_rules')
    op.drop_table('reward_rules')
