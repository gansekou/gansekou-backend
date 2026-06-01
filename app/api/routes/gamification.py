from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.badge import Badge
from app.models.student_badge import StudentBadge
from app.models.student_gamification import StudentGamification

from app.services.gamification_service import (
    get_or_create_profile,
    award_points,
    check_and_award_badges,
    ensure_default_badges,
    level_label,
)

router = APIRouter()


def require_student(user: User):
    if user.role != "ELEVE":
        raise HTTPException(status_code=403, detail="Accès réservé aux élèves")


def require_admin(user: User):
    if user.role not in ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration")


@router.get("/me/profile")
def get_my_gamification_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = get_or_create_profile(db, current_user.id)
    return {
        "id": profile.id,
        "student_id": profile.student_id,
        "points": profile.points,
        "level": profile.level,
        "level_label": level_label(profile.points, current_user.role),
        "quizzes_completed": profile.quizzes_completed,
        "quizzes_passed": profile.quizzes_passed,
        "current_streak_days": profile.current_streak_days,
        "best_streak_days": profile.best_streak_days,
        "last_activity_at": profile.last_activity_at,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


@router.get("/me/badges")
def get_my_badges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(StudentBadge)
        .filter(StudentBadge.student_id == current_user.id)
        .order_by(StudentBadge.earned_at.desc())
        .all()
    )


@router.get("/leaderboard")
def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(StudentGamification)
        .order_by(StudentGamification.points.desc())
        .limit(limit)
        .all()
    )


@router.post("/me/check-badges")
def check_my_badges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    badges = check_and_award_badges(db, current_user.id)

    return {
        "message": "Badges vérifiés",
        "new_badges": badges,
    }


@router.post("/admin/award-points/{student_id}")
def admin_award_points(
    student_id: str,
    points: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    profile = award_points(db, student_id, points)

    return {
        "message": "Points attribués",
        "profile": profile,
    }


@router.get("/badges")
def get_all_badges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_default_badges(db)
    return (
        db.query(Badge)
        .filter(Badge.is_active == True)
        .all()
    )
