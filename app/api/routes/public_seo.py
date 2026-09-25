from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models.content import Content
from app.schemas.public_seo import PublicSeoContentResponse


router = APIRouter()


@router.get(
    "/contents/{content_id}",
    response_model=PublicSeoContentResponse,
)
def get_public_seo_content(
    content_id: UUID,
    db: Session = Depends(get_db),
):
    db_content = (
        db.query(Content)
        .options(
            selectinload(Content.translations),
            selectinload(Content.subject),
            selectinload(Content.levels),
            selectinload(Content.specialties),
        ),
            selectinload(Content.levels),
            selectinload(Content.specialties),
        )
        .filter(
            Content.id == content_id,
            Content.status == "APPROVED",
            Content.content_type.in_(
                ["COURS", "EXERCICE", "SUJET"]
            ),
        )
        .first()
    )

    if db_content is None:
        raise HTTPException(
            status_code=404,
            detail="Contenu public introuvable",
        )

    translations = db_content.translations or []

    translation = next(
        (
            item
            for item in translations
            if item.language.lower() == "fr"
        ),
        None,
    )

    if translation is None:
        translation = next(
            (
                item
                for item in translations
                if item.language.lower() == "en"
            ),
            None,
        )

    if translation is None:
        raise HTTPException(
            status_code=404,
            detail="Traduction publique introuvable",
        )

    subject = db_content.subject

    return PublicSeoContentResponse(
        id=db_content.id,
        title=translation.title,
        description=(
            translation.description
            or translation.short_description
        ),
        content_type=db_content.content_type,
        content_format=db_content.content_format,
        subject_name=(
            subject.name_fr
            if subject is not None
            else None
        ),
        level_names=[
            level.name_fr
            for level in (db_content.levels or [])
        ],
        specialty_name=(
            db_content.specialties[0].name_fr
            if db_content.specialties
            else None
        ),
        thumbnail_url=db_content.thumbnail_url,
        is_premium=db_content.is_premium,
        published_at=db_content.published_at,
    )
