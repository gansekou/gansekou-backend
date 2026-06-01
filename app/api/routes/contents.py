from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.content import ContentCreate, ContentResponse
from app.schemas.content_translation import (
    ContentTranslationCreate,
    ContentTranslationResponse,
)
from app.crud.content import content, content_translation
from app.core.security import get_current_user, require_roles

from app.core.premium import require_premium_access, user_has_active_subscription
from app.core.content_access import (
    normalize_content_type,
    require_content_allowed_for_user,
    restrict_content_query_by_user,
)
from app.models.teacher_subject import TeacherSubject
from app.services.teacher_xp_service import (
    XP_CONTENT_DOWNLOAD,
    XP_CONTENT_VIEW,
    award_teacher_xp,
)

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]
CONTENT_CREATOR_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR", "ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"]
TEACHER_CREATOR_ROLES = ["ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"]


def can_access_premium(db: Session, current_user) -> bool:
    return current_user.role != "ELEVE" or user_has_active_subscription(db, current_user.id)


def restrict_premium_query(query, db: Session, current_user):
    if can_access_premium(db, current_user):
        return query

    return query.filter(content.model.is_premium == False)


def restrict_public_content_query(query, db: Session, current_user):
    query = query.filter(content.model.content_type.in_(["COURS", "EXERCICE", "SUJET"]))
    query = restrict_content_query_by_user(query, current_user, db)
    return restrict_premium_query(query, db, current_user)


def require_content_access(db: Session, current_user, db_content):
    require_content_allowed_for_user(db, current_user, db_content)
    if db_content.is_premium and current_user.role == "ELEVE":
        require_premium_access(db, current_user.id)


def teaches_content_subject(db: Session, current_user, db_content) -> bool:
    if current_user.role not in {"ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"}:
        return False

    return (
        db.query(TeacherSubject)
        .filter(
            TeacherSubject.teacher_id == current_user.id,
            TeacherSubject.subject_id == db_content.subject_id,
        )
        .first()
        is not None
    )


def require_content_download_access(db: Session, current_user, db_content):
    require_content_access(db, current_user, db_content)

    if current_user.role in {"ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"} and teaches_content_subject(db, current_user, db_content):
        if not user_has_active_subscription(db, current_user.id):
            raise HTTPException(status_code=403, detail="Abonnement premium enseignant requis pour télécharger ce contenu")


@router.post("/", response_model=ContentResponse)
def create_content(
    payload: ContentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(CONTENT_CREATOR_ROLES)),
):
    if current_user.role in TEACHER_CREATOR_ROLES:
        payload.author_id = current_user.id
        payload.status = "PENDING"

    payload.content_type = normalize_content_type(payload.content_type)
    return content.create(db, payload)


@router.get("/", response_model=list[ContentResponse])
def get_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return content.get_all(db, skip=skip, limit=limit)


@router.get("/approved", response_model=list[ContentResponse])
def get_approved_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(content.model).filter(content.model.status == "APPROVED")
    return restrict_public_content_query(query, db, current_user).offset(skip).limit(limit).all()


@router.get("/offline", response_model=list[ContentResponse])
def get_offline_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(content.model).filter(content.model.is_available_offline == True)
    return restrict_public_content_query(query, db, current_user).offset(skip).limit(limit).all()


@router.get("/by-level/{level_id}", response_model=list[ContentResponse])
def get_contents_by_level(
    level_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(content.model).filter(content.model.level_id == level_id)
    return restrict_public_content_query(query, db, current_user).offset(skip).limit(limit).all()


@router.get("/by-subject/{subject_id}", response_model=list[ContentResponse])
def get_contents_by_subject(
    subject_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(content.model).filter(content.model.subject_id == subject_id)
    return restrict_public_content_query(query, db, current_user).offset(skip).limit(limit).all()


@router.post("/translations", response_model=ContentTranslationResponse)
def create_content_translation(
    payload: ContentTranslationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(CONTENT_CREATOR_ROLES)),
):
    db_content = content.get(db, payload.content_id)

    if not db_content:
        raise HTTPException(status_code=404, detail="Contenu introuvable")

    if current_user.role in TEACHER_CREATOR_ROLES and db_content.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Un enseignant ne peut traduire que ses propres contenus",
        )

    return content_translation.create(db, payload)


@router.put("/translations/{translation_id}", response_model=ContentTranslationResponse)
def update_content_translation(
    translation_id: UUID,
    payload: ContentTranslationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(CONTENT_CREATOR_ROLES)),
):
    db_translation = content_translation.get(db, translation_id)

    if not db_translation:
        raise HTTPException(status_code=404, detail="Traduction introuvable")

    db_content = content.get(db, db_translation.content_id)

    if current_user.role in TEACHER_CREATOR_ROLES and db_content.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Un enseignant ne peut modifier que les traductions de ses propres contenus",
        )

    return content_translation.update(db, db_translation, payload)


@router.delete("/translations/{translation_id}", response_model=ContentTranslationResponse)
def delete_content_translation(
    translation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(CONTENT_CREATOR_ROLES)),
):
    db_translation = content_translation.get(db, translation_id)

    if not db_translation:
        raise HTTPException(status_code=404, detail="Traduction introuvable")

    db_content = content.get(db, db_translation.content_id)

    if current_user.role in TEACHER_CREATOR_ROLES and db_content.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Un enseignant ne peut supprimer que les traductions de ses propres contenus",
        )

    return content_translation.delete(db, translation_id)


@router.get("/{content_id}/translations", response_model=list[ContentTranslationResponse])
def get_content_translations(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(status_code=404, detail="Contenu introuvable")

    require_content_access(db, current_user, db_content)

    return content_translation.get_by_content(db, content_id)


@router.get("/{content_id}", response_model=ContentResponse)
def get_content(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(status_code=404, detail="Contenu introuvable")

    if db_content.status != "APPROVED" and current_user.role == "ELEVE":
        raise HTTPException(
            status_code=403,
            detail="Ce contenu n'est pas encore disponible pour les élèves",
        )
    
    require_content_access(db, current_user, db_content)

    return db_content


@router.put("/{content_id}", response_model=ContentResponse)
def update_content(
    content_id: UUID,
    payload: ContentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(CONTENT_CREATOR_ROLES)),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(status_code=404, detail="Contenu introuvable")

    if current_user.role in TEACHER_CREATOR_ROLES:
        if db_content.author_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Un enseignant ne peut modifier que ses propres contenus",
            )

        payload.author_id = current_user.id
        payload.status = "PENDING"

    payload.content_type = normalize_content_type(payload.content_type)
    return content.update(db, db_content, payload)


@router.delete("/{content_id}", response_model=ContentResponse)
def delete_content(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(CONTENT_CREATOR_ROLES)),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(status_code=404, detail="Contenu introuvable")

    if current_user.role in TEACHER_CREATOR_ROLES and db_content.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Un enseignant ne peut supprimer que ses propres contenus",
        )

    return content.delete(db, content_id)

@router.get("/me/my-contents", response_model=list[ContentResponse])
def get_my_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(CONTENT_CREATOR_ROLES)),
):
    return (
        db.query(content.model)
        .filter(content.model.author_id == current_user.id)
        .order_by(content.model.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

@router.get("/pending/review", response_model=list[ContentResponse])
def get_pending_review_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return (
        db.query(content.model)
        .filter(content.model.status == "PENDING")
        .order_by(content.model.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

@router.put("/{content_id}/publish", response_model=ContentResponse)
def publish_content(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(404, "Contenu introuvable")

    db_content.status = "APPROVED"

    db.commit()
    db.refresh(db_content)

    return db_content

@router.put("/{content_id}/archive", response_model=ContentResponse)
def archive_content(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(404, "Contenu introuvable")

    db_content.status = "ARCHIVED"

    db.commit()
    db.refresh(db_content)

    return db_content


@router.get("/search/", response_model=list[ContentResponse])
def search_contents(
    query: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_query = (
        db.query(content.model)
        .filter(
            content.model.status == "APPROVED",
            content.model.tags.ilike(f"%{query}%")
        )
    )
    return restrict_public_content_query(db_query, db, current_user).offset(skip).limit(limit).all()


@router.get("/by-type/{content_type}", response_model=list[ContentResponse])
def get_contents_by_type(
    content_type: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = (
        db.query(content.model)
        .filter(
            content.model.status == "APPROVED",
            content.model.content_type == normalize_content_type(content_type),
        )
    )
    return restrict_public_content_query(query, db, current_user).offset(skip).limit(limit).all()


@router.get("/premium/all", response_model=list[ContentResponse])
def get_premium_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role == "ELEVE":
        require_premium_access(db, current_user.id)

    query = db.query(content.model).filter(
        content.model.status == "APPROVED",
        content.model.is_premium == True,
    )
    return restrict_content_query_by_user(query, current_user, db).offset(skip).limit(limit).all()


@router.get("/featured/all", response_model=list[ContentResponse])
def get_featured_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = (
        db.query(content.model)
        .filter(
            content.model.status == "APPROVED",
            content.model.is_featured == True,
        )
    )
    return restrict_public_content_query(query, db, current_user).offset(skip).limit(limit).all()


@router.get("/popular/all", response_model=list[ContentResponse])
def get_popular_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(content.model).filter(content.model.status == "APPROVED")
    query = restrict_public_content_query(query, db, current_user)
    return query.order_by(content.model.total_views.desc()).offset(skip).limit(limit).all()


@router.get("/recent/all", response_model=list[ContentResponse])
def get_recent_contents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(content.model).filter(content.model.status == "APPROVED")
    query = restrict_public_content_query(query, db, current_user)
    return query.order_by(content.model.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/{content_id}/view")
def increment_content_view(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(404, "Contenu introuvable")

    require_content_access(db, current_user, db_content)

    db_content.total_views += 1
    if db_content.author_id != current_user.id:
        award_teacher_xp(db, db_content.author_id, XP_CONTENT_VIEW)

    db.commit()

    return {"message": "Vue enregistrée"}


@router.post("/{content_id}/download")
def increment_content_download(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(404, "Contenu introuvable")

    require_content_download_access(db, current_user, db_content)

    db_content.total_downloads += 1
    if db_content.author_id != current_user.id:
        award_teacher_xp(db, db_content.author_id, XP_CONTENT_DOWNLOAD)

    db.commit()

    return {"message": "Téléchargement enregistré"}


@router.post("/{content_id}/like")
def like_content(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(404, "Contenu introuvable")

    require_content_access(db, current_user, db_content)

    db_content.total_likes += 1

    db.commit()

    return {"message": "Like enregistré"}



@router.get("/{content_id}/analytics")
def get_content_analytics(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(404, "Contenu introuvable")

    return {
        "content_id": db_content.id,
        "views": db_content.total_views,
        "downloads": db_content.total_downloads,
        "likes": db_content.total_likes,
        "shares": db_content.total_shares,
        "rating": db_content.average_rating,
    }


@router.get("/{content_id}/related", response_model=list[ContentResponse])
def get_related_contents(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_content = content.get(db, content_id)

    if not db_content:
        raise HTTPException(404, "Contenu introuvable")

    require_content_access(db, current_user, db_content)

    query = (
        db.query(content.model)
        .filter(
            content.model.subject_id == db_content.subject_id,
            content.model.id != db_content.id,
            content.model.status == "APPROVED",
        )
    )
    return restrict_public_content_query(query, db, current_user).limit(20).all()


