from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models.content import Content
from app.models.content_translation import ContentTranslation
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
    # 1. Récupérer le contenu approuvé
    db_content = (
        db.query(Content)
        .options(
            selectinload(Content.subject),
            selectinload(Content.levels),
            selectinload(Content.specialties),
        )
        .filter(
            Content.id == content_id,
            Content.status == "APPROVED",
        )
        .first()
    )

    if db_content is None:
        raise HTTPException(
            status_code=404,
            detail="Contenu public introuvable",
        )

    # 2. Récupérer directement les traductions du contenu
    translations = (
        db.query(ContentTranslation)
        .filter(
            ContentTranslation.content_id == db_content.id
        )
        .all()
    )

    if not translations:
        raise HTTPException(
            status_code=404,
            detail="Aucune traduction trouvée pour ce contenu",
        )

    # 3. Priorité à la traduction française
    translation = next(
        (
            item
            for item in translations
            if item.language
            and item.language.upper() == "FR"
        ),
        None,
    )

    # 4. Sinon, utiliser la traduction anglaise
    if translation is None:
        translation = next(
            (
                item
                for item in translations
                if item.language
                and item.language.upper() == "EN"
            ),
            None,
        )

    # 5. Sinon, utiliser la première traduction disponible
    if translation is None:
        translation = translations[0]

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
