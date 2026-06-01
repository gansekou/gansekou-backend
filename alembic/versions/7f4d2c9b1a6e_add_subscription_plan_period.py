"""add subscription plan period

Revision ID: 7f4d2c9b1a6e
Revises: 0f4d2c1b9a10
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f4d2c9b1a6e"
down_revision: Union[str, Sequence[str], None] = "0f4d2c1b9a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column("period", sa.String(length=20), nullable=False, server_default="month"),
    )
    op.create_index(op.f("ix_subscription_plans_period"), "subscription_plans", ["period"], unique=False)
    op.execute(
        "UPDATE subscription_plans SET period = 'year' WHERE duration_days >= 330"
    )
    op.alter_column("subscription_plans", "period", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_subscription_plans_period"), table_name="subscription_plans")
    op.drop_column("subscription_plans", "period")
