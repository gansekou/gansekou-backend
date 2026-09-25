import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models.content import Content
from app.models.content_translation import ContentTranslation
from app.schemas.public_seo import PublicSeoContentResponse


router = APIRouter()


def extract_text_title(content_details: str | None) -> str | None:
    """
    Extrait un titre à partir du début d'un contenu TEXT.
    """

    if not content_details:
        return None

    lines = [
        line.strip()
        for line in content_details.splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    title = lines[0]

    # Nettoyage des espaces multiples
    title = re.sub(r"\s+", " ", title).strip()

    # Limite raisonnable pour un titre SEO
    if len(title) > 160:
        title = title[:157].rstrip() + "..."

    return title or None


def build_text_description(
    content_details: str | None,
    title: str,
) -> str | None:
    """
    Crée une description SEO à partir du contenu TEXT.
    """

    if not content_details:
        return None

    description = re.sub(
        r"\s+",
        " ",
        content_details,
    ).strip()

    # Éviter de répéter le titre au début de la description
    if description.startswith(title):
        description = description[len(title):].strip()

    if not description:
        return title

    # Limite adaptée à une description SEO
    if len(description) > 300:
        description = description[:297].rstrip() + "..."

    return description


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

    # 2. Récupérer les traductions existantes
    translations = (
        db.query(ContentTranslation)
        .filter(
            ContentTranslation.content_id == db_content.id
        )
        .all()
    )

    translation = next(
        (
            item
            for item in translations
            if item.language
            and item.language.upper() == "FR"
        ),
        None,
    )

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

    if translation is None and translations:
        translation = translations[0]

    # 3. Définir le titre et la description
    if translation is not None:
        title = translation.title

        description = (
            translation.description
            or translation.short_description
        )

    elif db_content.content_format == "TEXT":
        title = extract_text_title(
            db_content.content_details
        )

        if not title:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Le contenu TEXT ne possède pas "
                    "de titre exploitable"
                ),
            )

        description = build_text_description(
            db_content.content_details,
            title,
        )

    else:
        raise HTTPException(
            status_code=404,
            detail=(
                "Aucune traduction trouvée pour ce contenu"
            ),
        )

    subject = db_content.subject

    return PublicSeoContentResponse(
        id=db_content.id,
        title=title,
        description=description,
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
