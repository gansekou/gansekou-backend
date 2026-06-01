from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.content import Content
from app.models.content_translation import ContentTranslation


class CRUDContent(CRUDBase[Content]):
    def get_by_level(self, db: Session, level_id):
        return db.query(Content).filter(Content.level_id == level_id).all()

    def get_by_subject(self, db: Session, subject_id):
        return db.query(Content).filter(Content.subject_id == subject_id).all()

    def get_by_level_and_subject(self, db: Session, level_id, subject_id):
        return (
            db.query(Content)
            .filter(Content.level_id == level_id)
            .filter(Content.subject_id == subject_id)
            .all()
        )

    def get_approved(self, db: Session):
        return db.query(Content).filter(Content.status == "APPROVED").all()

    def get_offline_available(self, db: Session):
        return db.query(Content).filter(Content.is_available_offline == True).all()


class CRUDContentTranslation(CRUDBase[ContentTranslation]):
    def get_by_content(self, db: Session, content_id):
        return db.query(ContentTranslation).filter(ContentTranslation.content_id == content_id).all()

    def get_by_content_and_language(self, db: Session, content_id, language: str):
        return (
            db.query(ContentTranslation)
            .filter(ContentTranslation.content_id == content_id)
            .filter(ContentTranslation.language == language)
            .first()
        )


content = CRUDContent(Content)
content_translation = CRUDContentTranslation(ContentTranslation)