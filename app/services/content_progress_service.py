from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.content import Content
from app.models.content_progress import ContentProgress
from app.models.content_favorite import ContentFavorite
from app.models.content_rating import ContentRating

from app.core.premium import require_premium_access
from app.services.gamification_service import award_points

XP_CONTENT_START = 5
XP_CONTENT_COMPLETE = 20
XP_CONTENT_DOWNLOAD = 3

def get_content_or_404(db: Session, content_id):
    return db.query(Content).filter(Content.id == content_id).first()


def require_content_access(db: Session, student_id, content: Content):
    if content.is_premium:
        require_premium_access(db, student_id)


def get_or_create_progress(db: Session, student_id, content_id):
    progress = (
        db.query(ContentProgress)
        .filter(
            ContentProgress.student_id == student_id,
            ContentProgress.content_id == content_id,
        )
        .first()
    )

    if progress:
        return progress

    now = datetime.now(timezone.utc)

    progress = ContentProgress(
        student_id=student_id,
        content_id=content_id,
        is_started=True,
        progress_percent=0,
        started_at=now,
        last_accessed_at=now,
    )

    db.add(progress)
    db.commit()
    db.refresh(progress)

    return progress


def start_content(db: Session, student_id, content_id):
    content = get_content_or_404(db, content_id)

    if not content:
        return None

    require_content_access(db, student_id, content)

    existing_started = (
        db.query(ContentProgress)
        .filter(
            ContentProgress.student_id == student_id,
            ContentProgress.content_id == content_id,
        )
        .first()
    )

    progress = get_or_create_progress(db, student_id, content_id)

    now = datetime.now(timezone.utc)

    progress.is_started = True
    progress.last_accessed_at = now

    if not progress.started_at:
        progress.started_at = now

    content.total_views += 1

    db.commit()
    db.refresh(progress)

    if not existing_started:
        award_points(db, student_id, XP_CONTENT_START)

    return progress


def update_content_progress(
    db: Session,
    student_id,
    content_id,
    progress_percent: int,
    time_spent_minutes: int = 0,
):
    content = get_content_or_404(db, content_id)

    if not content:
        return None

    require_content_access(db, student_id, content)

    progress = get_or_create_progress(db, student_id, content_id)

    progress.progress_percent = max(0, min(progress_percent, 100))
    progress.time_spent_minutes += time_spent_minutes
    progress.last_accessed_at = datetime.now(timezone.utc)

    was_completed = progress.is_completed

    if progress.progress_percent >= 100:
        progress.is_completed = True
        progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)

    if progress.is_completed and not was_completed:
        award_points(db, student_id, XP_CONTENT_COMPLETE)

    return progress


def complete_content(db: Session, student_id, content_id):
    content = get_content_or_404(db, content_id)

    if not content:
        return None

    require_content_access(db, student_id, content)

    progress = get_or_create_progress(db, student_id, content_id)

    was_completed = progress.is_completed
    progress.progress_percent = 100
    progress.is_started = True
    progress.is_completed = True
    progress.completed_at = datetime.now(timezone.utc)
    progress.last_accessed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)

    if not was_completed:
        award_points(db, student_id, XP_CONTENT_COMPLETE)

    return progress


def add_favorite(db: Session, student_id, content_id):
    content = get_content_or_404(db, content_id)

    if not content:
        return None

    require_content_access(db, student_id, content)

    existing = (
        db.query(ContentFavorite)
        .filter(
            ContentFavorite.student_id == student_id,
            ContentFavorite.content_id == content_id,
        )
        .first()
    )

    if existing:
        return existing

    favorite = ContentFavorite(
        student_id=student_id,
        content_id=content_id,
    )

    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return favorite


def remove_favorite(db: Session, student_id, content_id):
    content = get_content_or_404(db, content_id)

    if not content:
        return None

    require_content_access(db, student_id, content)

    favorite = (
        db.query(ContentFavorite)
        .filter(
            ContentFavorite.student_id == student_id,
            ContentFavorite.content_id == content_id,
        )
        .first()
    )

    if not favorite:
        return None

    db.delete(favorite)
    db.commit()

    return True


def rate_content(db: Session, student_id, content_id, rating: int, review: str | None = None):
    content = get_content_or_404(db, content_id)

    if not content:
        return None

    require_content_access(db, student_id, content)

    existing = (
        db.query(ContentRating)
        .filter(
            ContentRating.student_id == student_id,
            ContentRating.content_id == content_id,
        )
        .first()
    )

    if existing:
        existing.rating = rating
        existing.review = review
        db.commit()
        db.refresh(existing)
        rating_obj = existing
    else:
        rating_obj = ContentRating(
            student_id=student_id,
            content_id=content_id,
            rating=rating,
            review=review,
        )

        db.add(rating_obj)
        db.commit()
        db.refresh(rating_obj)

    avg_rating = (
        db.query(func.avg(ContentRating.rating))
        .filter(ContentRating.content_id == content_id)
        .scalar()
    )

    if avg_rating is not None:
        content.average_rating = int(round(avg_rating))

    db.commit()

    return rating_obj


def register_download(db: Session, student_id, content_id):
    content = get_content_or_404(db, content_id)

    if not content:
        return None
    
    require_content_access(db, student_id, content)

    content.total_downloads += 1

    progress = get_or_create_progress(db, student_id, content_id)
    progress.last_accessed_at = datetime.now(timezone.utc)

    db.commit()

    award_points(db, student_id, XP_CONTENT_DOWNLOAD)

    return {
        "message": "Téléchargement enregistré",
        "content_id": content_id,
    }


def get_my_progress(db: Session, student_id):
    return (
        db.query(ContentProgress)
        .filter(ContentProgress.student_id == student_id)
        .order_by(ContentProgress.updated_at.desc())
        .all()
    )


def get_my_completed(db: Session, student_id):
    return (
        db.query(ContentProgress)
        .filter(
            ContentProgress.student_id == student_id,
            ContentProgress.is_completed == True,
        )
        .order_by(ContentProgress.completed_at.desc())
        .all()
    )


def get_my_favorites(db: Session, student_id):
    return (
        db.query(ContentFavorite)
        .filter(ContentFavorite.student_id == student_id)
        .order_by(ContentFavorite.created_at.desc())
        .all()
    )


def get_my_ratings(db: Session, student_id):
    return (
        db.query(ContentRating)
        .filter(ContentRating.student_id == student_id)
        .order_by(ContentRating.updated_at.desc())
        .all()
    )


def get_my_content_stats(db: Session, student_id):
    total_started = (
        db.query(ContentProgress)
        .filter(ContentProgress.student_id == student_id)
        .count()
    )

    total_completed = (
        db.query(ContentProgress)
        .filter(
            ContentProgress.student_id == student_id,
            ContentProgress.is_completed == True,
        )
        .count()
    )

    total_favorites = (
        db.query(ContentFavorite)
        .filter(ContentFavorite.student_id == student_id)
        .count()
    )

    total_ratings = (
        db.query(ContentRating)
        .filter(ContentRating.student_id == student_id)
        .count()
    )

    total_time_spent = (
        db.query(func.coalesce(func.sum(ContentProgress.time_spent_minutes), 0))
        .filter(ContentProgress.student_id == student_id)
        .scalar()
    )

    completion_rate = 0

    if total_started > 0:
        completion_rate = round((total_completed / total_started) * 100, 2)

    return {
        "total_started": total_started,
        "total_completed": total_completed,
        "total_favorites": total_favorites,
        "total_ratings": total_ratings,
        "total_time_spent_minutes": total_time_spent,
        "completion_rate_percent": completion_rate,
    }
