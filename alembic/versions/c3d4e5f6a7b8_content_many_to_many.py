"""Convert Content level/specialty to many-to-many relations.

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-08-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # 1. Création de la table content_levels
    # ============================================================

    op.create_table(
        "content_levels",
        sa.Column(
            "content_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "contents.id",
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

    # ============================================================
    # 2. Création de la table content_specialties
    # ============================================================

    op.create_table(
        "content_specialties",
        sa.Column(
            "content_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "contents.id",
                ondelete="CASCADE",
            ),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "specialty_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "specialties.id",
                ondelete="CASCADE",
            ),
            primary_key=True,
            nullable=False,
        ),
    )

    # ============================================================
    # 3. Migration des niveaux existants
    #
    # contents.level_id
    #       ↓
    # content_levels
    # ============================================================

    op.execute(
        """
        INSERT INTO content_levels (
            content_id,
            level_id
        )
        SELECT
            id,
            level_id
        FROM contents
        WHERE level_id IS NOT NULL
        """
    )

    # ============================================================
    # 4. Migration des spécialités existantes
    #
    # contents.specialty_id
    #       ↓
    # content_specialties
    # ============================================================

    op.execute(
        """
        INSERT INTO content_specialties (
            content_id,
            specialty_id
        )
        SELECT
            id,
            specialty_id
        FROM contents
        WHERE specialty_id IS NOT NULL
        """
    )

    # ============================================================
    # 5. Suppression des anciennes colonnes
    # ============================================================

    op.drop_column(
        "contents",
        "level_id",
    )

    op.drop_column(
        "contents",
        "specialty_id",
    )


def downgrade() -> None:
    # ============================================================
    # 1. Restaurer level_id
    # ============================================================

    op.add_column(
        "contents",
        sa.Column(
            "level_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # ============================================================
    # 2. Restaurer specialty_id
    # ============================================================

    op.add_column(
        "contents",
        sa.Column(
            "specialty_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # ============================================================
    # 3. Restaurer les anciennes associations
    #
    # Un ancien Content ne pouvait avoir qu'un seul niveau
    # et une seule spécialité.
    #
    # Si plusieurs associations ont été ajoutées après la migration,
    # on conserve la première association pour le downgrade.
    # ============================================================

    op.execute(
        """
        UPDATE contents AS c
        SET level_id = cl.level_id
        FROM (
            SELECT DISTINCT ON (content_id)
                content_id,
                level_id
            FROM content_levels
            ORDER BY content_id, level_id
        ) AS cl
        WHERE c.id = cl.content_id
        """
    )

    op.execute(
        """
        UPDATE contents AS c
        SET specialty_id = cs.specialty_id
        FROM (
            SELECT DISTINCT ON (content_id)
                content_id,
                specialty_id
            FROM content_specialties
            ORDER BY content_id, specialty_id
        ) AS cs
        WHERE c.id = cs.content_id
        """
    )

    # ============================================================
    # 4. Supprimer les tables many-to-many
    # ============================================================

    op.drop_table(
        "content_specialties",
    )

    op.drop_table(
        "content_levels",
    )
