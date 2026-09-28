"""add password_resets table

Revision ID: 0c6f4ea77c10
Revises: d1021e0a401e
Create Date: 2026-09-28 21:04:38.506156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c6f4ea77c10'
down_revision: Union[str, None] = 'd1021e0a401e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'password_resets',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_password_resets_token_hash'),
        'password_resets',
        ['token_hash'],
        unique=True,
    )
    op.create_index(
        op.f('ix_password_resets_user_id'),
        'password_resets',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_password_resets_user_id'), table_name='password_resets')
    op.drop_index(op.f('ix_password_resets_token_hash'), table_name='password_resets')
    op.drop_table('password_resets')
