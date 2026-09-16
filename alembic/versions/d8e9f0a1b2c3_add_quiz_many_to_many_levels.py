"""Add many-to-many levels to quizzes.

Revision ID: d8e9f0a1b2c3
Revises: c3d4e5f6a7b8
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d8e9f0a1b2c3"

down_revision: Union[
    str,
    Sequence[str],
    None
] = "c3d4e5f6a7b8"

branch_labels: Union[
    str,
    Sequence[str],
    None
] = None

depends_on: Union[
    str,
    Sequence[str],
    None
] = None


def upgrade() -> None:

    # ============================================================
    # 1. TABLE QUIZ_LEVELS
    # ============================================================

    op.create_table(
        "quiz_levels",

        sa.Column(
            "quiz_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "quizzes.id",
                ondelete="CASCADE",
            ),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "level_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "levels.id",
                ondelete="CASCADE",
            ),
            primary_key=True,
            nullable=False,
        ),
    )

    op.create_index(
        "ix_quiz_levels_level_id",
        "quiz_levels",
        ["level_id"],
        unique=False,
    )

    # ============================================================
    # 2. MIGRER LES ANCIENS QUIZ
    #
    # quizzes.level_id
    #        ↓
    # quiz_levels
    # ============================================================

    op.execute(
        """
        INSERT INTO quiz_levels (
            quiz_id,
            level_id
        )
        SELECT
            id,
            level_id
        FROM quizzes
        WHERE level_id IS NOT NULL
        """
    )


def downgrade() -> None:

    op.drop_index(
        "ix_quiz_levels_level_id",
        table_name="quiz_levels",
    )

    op.drop_table(
        "quiz_levels"
    )
