import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.quiz_attempt import QuizAttempt

from app.services.adaptive_learning_service import (
    analyze_quiz_attempt,
    get_student_profile,
    get_student_weaknesses,
    get_student_progress,
    get_recommendations,
)

router = APIRouter()


def require_student(current_user: User):
    if current_user.role != "ELEVE":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux élèves"
        )


@router.post("/analyze-attempt/{attempt_id}")
def analyze_attempt(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.id == attempt_id,
            QuizAttempt.student_id == current_user.id,
        )
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Tentative introuvable"
        )

    result = analyze_quiz_attempt(db, attempt_id)

    if not result:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'analyser cette tentative"
        )

    return {
        "message": "Tentative analysée avec succès"
    }


@router.get("/me/profile")
def get_my_adaptive_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    return get_student_profile(db, current_user.id)


@router.get("/me/weaknesses")
def get_my_weaknesses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    return get_student_weaknesses(db, current_user.id)


@router.get("/me/progress")
def get_my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    return get_student_progress(db, current_user.id)


@router.get("/me/recommendations")
def get_my_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    return get_recommendations(db, current_user.id)