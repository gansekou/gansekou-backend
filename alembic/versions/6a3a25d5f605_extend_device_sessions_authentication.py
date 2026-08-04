"""extend device sessions authentication

Revision ID: 6a3a25d5f605
Revises: a261ceb5ac95
Create Date: 2026-08-04 09:08:41.159318

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6a3a25d5f605"
down_revision: Union[str, Sequence[str], None] = "a261ceb5ac95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "device_sessions",
        sa.Column(
            "refresh_token_hash",
            sa.String(length=255),
            nullable=True
        )
    )

    op.add_column(
        "device_sessions",
        sa.Column(
            "last_activity",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False
        )
    )

    op.add_column(
        "device_sessions",
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    op.add_column(
        "device_sessions",
        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false")
        )
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        "device_sessions",
        "revoked"
    )

    op.drop_column(
        "device_sessions",
        "expires_at"
    )

    op.drop_column(
        "device_sessions",
        "last_activity"
    )

    op.drop_column(
        "device_sessions",
        "refresh_token_hash"
    )
