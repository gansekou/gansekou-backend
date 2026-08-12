"""add monetbil payment id

Revision ID: b7c8d9e0f1a2
Revises: 6a3a25d5f605
Create Date: 2026-08-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "6a3a25d5f605"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_transactions",
        sa.Column(
            "monetbil_payment_id",
            sa.String(length=150),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_payment_transactions_monetbil_payment_id",
        "payment_transactions",
        ["monetbil_payment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_transactions_monetbil_payment_id",
        table_name="payment_transactions",
    )

    op.drop_column(
        "payment_transactions",
        "monetbil_payment_id",
    )
