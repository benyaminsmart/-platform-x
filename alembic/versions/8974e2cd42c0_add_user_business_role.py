"""add user business_role

Revision ID: 8974e2cd42c0
Revises: 0c6f4ea77c10
Create Date: 2026-09-28 21:28:02.705202

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8974e2cd42c0'
down_revision: Union[str, None] = '0c6f4ea77c10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('business_role', sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'business_role')
