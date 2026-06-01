import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user
from app.core.content_access import require_content_allowed_for_user, restrict_quiz_query_by_user

from app.models.user import User
from app.models.content import Content
from app.models.quiz import Quiz

from app.schemas.content_progress import (
    ContentProgressUpdate,
    ContentRatingCreate,
    ContentProgressResponse,
    ContentFavoriteResponse,
    ContentRatingResponse,
)

from app.services.content_progress_service import (
    start_content,
    update_content_progress,
    complete_content,
    add_favorite,
    remove_favorite,
    rate_content,
    register_download,
    get_my_progress,
    get_my_completed,
    get_my_favorites,
    get_my_ratings,
    get_my_content_stats,
)

router = APIRouter()


def require_learning_content(db: Session, current_user: User, content_id: uuid.UUID):
    db_content = db.query(Content).filter(Content.id == content_id).first()
    if not db_content:
        raise HTTPException(404, "Contenu introuvable")
    require_content_allowed_for_user(db, current_user, db_content)
    return db_content


def require_student(current_user: User):
    if current_user.role != "ELEVE":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux élèves"
        )


@router.post("/{content_id}/start", response_model=ContentProgressResponse)
def start_learning_content(
    content_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    progress = start_content(
        db=db,
        student_id=current_user.id,
        content_id=content_id,
    )

    if not progress:
        raise HTTPException(404, "Contenu introuvable")

    return progress


@router.put("/{content_id}/progress", response_model=ContentProgressResponse)
def update_learning_progress(
    content_id: uuid.UUID,
    payload: ContentProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    progress = update_content_progress(
        db=db,
        student_id=current_user.id,
        content_id=content_id,
        progress_percent=payload.progress_percent,
        time_spent_minutes=payload.time_spent_minutes,
    )

    if not progress:
        raise HTTPException(404, "Contenu introuvable")

    return progress


@router.post("/{content_id}/complete")
def complete_learning_content(
    content_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    db_content = db.query(Content).filter(Content.id == content_id).first()
    if not db_content:
        raise HTTPException(404, "Contenu introuvable")
    require_content_allowed_for_user(db, current_user, db_content)

    progress = complete_content(
        db=db,
        student_id=current_user.id,
        content_id=content_id,
    )

    if not progress:
        raise HTTPException(404, "Contenu introuvable")

    linked_query = db.query(Quiz).filter(
        Quiz.status == "PUBLISHED",
        Quiz.course_id == content_id,
    )
    linked_query = restrict_quiz_query_by_user(linked_query, current_user, db)
    linked_quizzes = linked_query.limit(20).all()

    return {
        "completed": True,
        "progress": ContentProgressResponse.model_validate(progress),
        "linked_quizzes": linked_quizzes,
    }


@router.post("/{content_id}/favorite", response_model=ContentFavoriteResponse)
def favorite_content(
    content_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    favorite = add_favorite(
        db=db,
        student_id=current_user.id,
        content_id=content_id,
    )

    if not favorite:
        raise HTTPException(404, "Contenu introuvable")

    return favorite


@router.delete("/{content_id}/favorite")
def unfavorite_content(
    content_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    removed = remove_favorite(
        db=db,
        student_id=current_user.id,
        content_id=content_id,
    )

    if not removed:
        raise HTTPException(404, "Favori introuvable")

    return {"message": "Favori retiré avec succès"}


@router.post("/{content_id}/rate", response_model=ContentRatingResponse)
def rate_learning_content(
    content_id: uuid.UUID,
    payload: ContentRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    rating = rate_content(
        db=db,
        student_id=current_user.id,
        content_id=content_id,
        rating=payload.rating,
        review=payload.review,
    )

    if not rating:
        raise HTTPException(404, "Contenu introuvable")

    return rating


@router.post("/{content_id}/download")
def download_learning_content(
    content_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    result = register_download(
        db=db,
        student_id=current_user.id,
        content_id=content_id,
    )

    if not result:
        raise HTTPException(404, "Contenu introuvable")

    return result


@router.get("/me/progress", response_model=list[ContentProgressResponse])
def get_my_learning_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    return get_my_progress(db, current_user.id)


@router.get("/me/completed", response_model=list[ContentProgressResponse])
def get_my_completed_contents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    return get_my_completed(db, current_user.id)


@router.get("/me/favorites", response_model=list[ContentFavoriteResponse])
def get_my_favorite_contents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    return get_my_favorites(db, current_user.id)


@router.get("/me/ratings", response_model=list[ContentRatingResponse])
def get_my_content_ratings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    return get_my_ratings(db, current_user.id)


@router.get("/me/stats")
def get_my_learning_content_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    return get_my_content_stats(db, current_user.id)
