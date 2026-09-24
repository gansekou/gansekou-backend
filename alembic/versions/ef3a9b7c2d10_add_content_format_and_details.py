
"""add content format and markdown details

Revision ID: ef3a9b7c2d10
Revises: d8e9f0a1b2c3
"""

from alembic import op
import sqlalchemy as sa


revision = "ef3a9b7c2d10"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "contents",
        sa.Column(
            "content_format",
            sa.String(length=20),
            nullable=True,
            server_default="PDF",
        ),
    )

    op.add_column(
        "contents",
        sa.Column(
            "content_details",
            sa.Text(),
            nullable=True,
        ),
    )

    op.alter_column(
        "contents",
        "content_format",
        nullable=False,
    )


def downgrade():
    op.drop_column(
        "contents",
        "content_details",
    )

    op.drop_column(
        "contents",
        "content_format",
    )
