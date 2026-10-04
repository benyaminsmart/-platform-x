"""phase-77 step-1 referral engine: code + relationship + event + reward

Revision ID: b1a2c3d4e5f7
Revises: 2d0c88d97959
Create Date: 2026-10-02 20:16:00.000000

Hand-written (SQLite-safe):
- creates four new tables: referral_codes, referral_relationships,
  referral_events, referral_rewards
- leaves the legacy `referrals` table untouched (it will be dropped
  in a later Phase 77 step once the new engine is wired in)
- seeds one default ReferralCode per existing user from
  `users.referral_code` so the new engine has a code for everyone
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1a2c3d4e5f7'
down_revision: Union[str, None] = '2d0c88d97959'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- referral_codes ---
    op.create_table(
        'referral_codes',
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_referral_codes_tenant', 'referral_codes', ['tenant_id'], unique=False)
    op.create_index('ix_referral_codes_user', 'referral_codes', ['user_id'], unique=False)
    op.create_index('ix_referral_codes_code', 'referral_codes', ['code'], unique=True)

    # --- referral_relationships ---
    op.create_table(
        'referral_relationships',
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('referral_code_id', sa.String(length=36), nullable=False),
        sa.Column('referrer_user_id', sa.String(length=36), nullable=False),
        sa.Column('referred_user_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='INVITED'),
        sa.Column('registered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('qualified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rewarded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reversed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('qualifying_booking_id', sa.String(length=36), nullable=True),
        sa.Column('review_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['referral_code_id'], ['referral_codes.id']),
        sa.ForeignKeyConstraint(['referrer_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['referred_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_referral_relationships_tenant', 'referral_relationships', ['tenant_id'], unique=False)
    op.create_index('ix_referral_relationships_referrer', 'referral_relationships', ['referrer_user_id', 'status'], unique=False)
    op.create_index('ix_referral_relationships_referred', 'referral_relationships', ['referred_user_id'], unique=False)
    op.create_index('ix_referral_relationships_code', 'referral_relationships', ['referral_code_id'], unique=False)

    # --- referral_events ---
    op.create_table(
        'referral_events',
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('relationship_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status', sa.String(length=20), nullable=True),
        sa.Column('actor_user_id', sa.String(length=36), nullable=True),
        sa.Column('extra', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['relationship_id'], ['referral_relationships.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_referral_events_tenant', 'referral_events', ['tenant_id'], unique=False)
    op.create_index('ix_referral_events_relationship', 'referral_events', ['relationship_id', 'created_at'], unique=False)
    op.create_index('ix_referral_events_type', 'referral_events', ['event_type'], unique=False)

    # --- referral_rewards ---
    op.create_table(
        'referral_rewards',
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('relationship_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='AED'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('ledger_reward_id', sa.String(length=36), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reversed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['relationship_id'], ['referral_relationships.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['ledger_reward_id'], ['rewards.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_referral_rewards_relationship', 'referral_rewards', ['relationship_id'], unique=False)
    op.create_index('ix_referral_rewards_user', 'referral_rewards', ['user_id', 'status'], unique=False)
    op.create_index('ix_referral_rewards_ledger', 'referral_rewards', ['ledger_reward_id'], unique=False)

    # --- data backfill: one default ReferralCode per existing user ---
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, tenant_id, referral_code FROM users "
        "WHERE referral_code IS NOT NULL AND referral_code != ''"
    )).fetchall()

    import uuid as _uuid
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for uid, tid, code in rows:
        conn.execute(sa.text(
            "INSERT INTO referral_codes "
            "(id, tenant_id, user_id, code, is_default, is_active, "
            " created_at, updated_at) "
            "VALUES (:id, :tid, :uid, :code, 1, 1, :now, :now)"
        ), {
            "id": str(_uuid.uuid4()),
            "tid": tid,
            "uid": uid,
            "code": code,
            "now": now,
        })


def downgrade() -> None:
    op.drop_index('ix_referral_rewards_ledger', table_name='referral_rewards')
    op.drop_index('ix_referral_rewards_user', table_name='referral_rewards')
    op.drop_index('ix_referral_rewards_relationship', table_name='referral_rewards')
    op.drop_table('referral_rewards')

    op.drop_index('ix_referral_events_type', table_name='referral_events')
    op.drop_index('ix_referral_events_relationship', table_name='referral_events')
    op.drop_index('ix_referral_events_tenant', table_name='referral_events')
    op.drop_table('referral_events')

    op.drop_index('ix_referral_relationships_code', table_name='referral_relationships')
    op.drop_index('ix_referral_relationships_referred', table_name='referral_relationships')
    op.drop_index('ix_referral_relationships_referrer', table_name='referral_relationships')
    op.drop_index('ix_referral_relationships_tenant', table_name='referral_relationships')
    op.drop_table('referral_relationships')

    op.drop_index('ix_referral_codes_code', table_name='referral_codes')
    op.drop_index('ix_referral_codes_user', table_name='referral_codes')
    op.drop_index('ix_referral_codes_tenant', table_name='referral_codes')
    op.drop_table('referral_codes')
