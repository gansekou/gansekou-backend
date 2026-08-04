"""add user sessions

Revision ID: 89901e0b477a
Revises: a261ceb5ac95
Create Date: 2026-08-04 08:36:26.294891

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "89901e0b477a"
down_revision: Union[str, Sequence[str], None] = "a261ceb5ac95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "user_sessions",

        sa.Column(
            "id",
            sa.String(),
            nullable=False
        ),

        sa.Column(
            "user_id",
            sa.String(),
            nullable=False
        ),

        sa.Column(
            "refresh_token_hash",
            sa.String(),
            nullable=False
        ),

        sa.Column(
            "device_name",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "ip_address",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True
        ),

        sa.Column(
            "last_activity",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True
        ),

        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False
        ),

        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false")
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"]
        ),

        sa.PrimaryKeyConstraint(
            "id"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("user_sessions")
