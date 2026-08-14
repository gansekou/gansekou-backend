from sqlalchemy.orm import Session

from app.crud.base import CRUDBase

from app.models.content import Content
from app.models.content_relation import ContentRelation
from app.models.content_translation import ContentTranslation
from app.models.content_level import ContentLevel
from app.models.content_specialty import ContentSpecialty
from app.models.level import Level
from app.models.specialty import Specialty


class CRUDContent(CRUDBase[Content]):

    def create(self, db: Session, obj_in):
        obj_data = obj_in.model_dump(exclude_unset=True)

        # ---------------------------------------------------------
        # Récupérer les relations avant de créer Content
        # ---------------------------------------------------------

        related_content_ids = obj_data.pop(
            "related_content_ids",
            []
        )

        level_ids = obj_data.pop(
            "level_ids",
            []
        )

        specialty_ids = obj_data.pop(
            "specialty_ids",
            []
        )

        try:
            # -----------------------------------------------------
            # 1. Créer le contenu
            # -----------------------------------------------------

            db_obj = Content(**obj_data)

            db.add(db_obj)

            # Génère db_obj.id
            db.flush()

            # -----------------------------------------------------
            # 2. Associer les niveaux
            # -----------------------------------------------------

            for level_id in level_ids:

                level = (
                    db.query(Level)
                    .filter(Level.id == level_id)
                    .first()
                )

                if level:
                    db_obj.levels.append(level)

            # -----------------------------------------------------
            # 3. Associer les spécialités
            # -----------------------------------------------------

            for specialty_id in specialty_ids:

                specialty = (
                    db.query(Specialty)
                    .filter(Specialty.id == specialty_id)
                    .first()
                )

                if specialty:
                    db_obj.specialties.append(specialty)

            # -----------------------------------------------------
            # 4. Relations pédagogiques
            # -----------------------------------------------------

            for related_id in related_content_ids:

                db.add(
                    ContentRelation(
                        parent_content_id=db_obj.id,
                        child_content_id=related_id,
                        relation_type="HAS_EXERCISE",
                    )
                )

            # -----------------------------------------------------
            # 5. Sauvegarder
            # -----------------------------------------------------

            db.commit()

            db.refresh(db_obj)

            return db_obj

        except Exception:
            db.rollback()
            raise

    # =============================================================
    # NIVEAUX
    # =============================================================

    def get_by_level(
        self,
        db: Session,
        level_id,
    ):
        return (
            db.query(Content)
            .join(
                ContentLevel,
                ContentLevel.content_id == Content.id,
            )
            .filter(
                ContentLevel.level_id == level_id
            )
            .all()
        )

    # =============================================================
    # MATIÈRE
    # =============================================================

    def get_by_subject(
        self,
        db: Session,
        subject_id,
    ):
        return (
            db.query(Content)
            .filter(
                Content.subject_id == subject_id
            )
            .all()
        )

    # =============================================================
    # NIVEAU + MATIÈRE
    # =============================================================

    def get_by_level_and_subject(
        self,
        db: Session,
        level_id,
        subject_id,
    ):
        return (
            db.query(Content)
            .join(
                ContentLevel,
                ContentLevel.content_id == Content.id,
            )
            .filter(
                ContentLevel.level_id == level_id
            )
            .filter(
                Content.subject_id == subject_id
            )
            .all()
        )

    # =============================================================
    # NIVEAU + MATIÈRE + TYPE
    # =============================================================

    def get_by_level_subject_and_type(
        self,
        db: Session,
        level_id,
        subject_id,
        content_type,
    ):
        return (
            db.query(Content)
            .join(
                ContentLevel,
                ContentLevel.content_id == Content.id,
            )
            .filter(
                ContentLevel.level_id == level_id
            )
            .filter(
                Content.subject_id == subject_id
            )
            .filter(
                Content.content_type == content_type
            )
            .filter(
                Content.status == "APPROVED"
            )
            .all()
        )

    # =============================================================
    # CONTENUS APPROUVÉS
    # =============================================================

    def get_approved(
        self,
        db: Session,
    ):
        return (
            db.query(Content)
            .filter(
                Content.status == "APPROVED"
            )
            .all()
        )

    # =============================================================
    # CONTENUS DISPONIBLES HORS-LIGNE
    # =============================================================

    def get_offline_available(
        self,
        db: Session,
    ):
        return (
            db.query(Content)
            .filter(
                Content.is_available_offline == True
            )
            .all()
        )


# =================================================================
# TRADUCTIONS
# =================================================================

class CRUDContentTranslation(
    CRUDBase[ContentTranslation]
):

    def get_by_content(
        self,
        db: Session,
        content_id,
    ):
        return (
            db.query(ContentTranslation)
            .filter(
                ContentTranslation.content_id == content_id
            )
            .all()
        )

    def get_by_content_and_language(
        self,
        db: Session,
        content_id,
        language: str,
    ):
        return (
            db.query(ContentTranslation)
            .filter(
                ContentTranslation.content_id == content_id
            )
            .filter(
                ContentTranslation.language == language
            )
            .first()
        )


# =================================================================
# INSTANCES CRUD
# =================================================================

content = CRUDContent(Content)

content_translation = CRUDContentTranslation(
    ContentTranslation
)
