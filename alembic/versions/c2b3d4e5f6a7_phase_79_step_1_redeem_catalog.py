"""phase-79 step-1: extend redeem_options with platform_cost + funding_source + category

Revision ID: c2b3d4e5f6a7
Revises: b1a2c3d4e5f7
Create Date: 2026-10-04 18:35:00.000000

Hand-written (SQLite-safe):
- adds three nullable columns to redeem_options so the new catalog can
  carry platform_cost, funding_source, and category.
- no data backfill — old rows simply have NULL in the new columns and
  remain usable (fallback defaults apply in the service).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2b3d4e5f6a7'
down_revision: Union[str, None] = 'b1a2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'redeem_options',
        sa.Column('platform_cost', sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        'redeem_options',
        sa.Column('funding_source', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'redeem_options',
        sa.Column('category', sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('redeem_options', 'category')
    op.drop_column('redeem_options', 'funding_source')
    op.drop_column('redeem_options', 'platform_cost')
