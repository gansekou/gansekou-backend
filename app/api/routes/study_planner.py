import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user

from app.models.user import User

from app.schemas.study_planner import (
    StudyPlanGenerateRequest,
    StudyPlanResponse,
    StudyPlanItemResponse,
)

from app.services.study_planner_service import (
    generate_study_plan,
    get_active_plan,
    get_plan_items,
    get_student_plan_history,
    get_today_items,
    complete_item,
)

router = APIRouter()


def require_student(current_user: User):
    if current_user.role != "ELEVE":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux élèves"
        )


@router.post("/generate", response_model=StudyPlanResponse)
def generate_my_study_plan(
    payload: StudyPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    return generate_study_plan(
        db=db,
        student_id=current_user.id,
        title=payload.title,
        language=payload.language,
        duration_days=payload.duration_days,
        max_items=payload.max_items,
    )


@router.get("/me/current", response_model=StudyPlanResponse)
def get_my_current_study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    plan = get_active_plan(db, current_user.id)

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Aucun plan actif trouvé"
        )

    return plan


@router.get("/me/current/items", response_model=list[StudyPlanItemResponse])
def get_my_current_study_plan_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    plan = get_active_plan(db, current_user.id)

    if not plan:
        return []

    return get_plan_items(db, plan.id)


@router.get("/me/history", response_model=list[StudyPlanResponse])
def get_my_study_plan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    return get_student_plan_history(db, current_user.id)


@router.get("/me/today", response_model=list[StudyPlanItemResponse])
def get_my_today_study_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    return get_today_items(db, current_user.id)


@router.put("/items/{item_id}/complete", response_model=StudyPlanItemResponse)
def complete_study_plan_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    item = complete_item(
        db=db,
        item_id=item_id,
        student_id=current_user.id,
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Élément du plan introuvable"
        )

    return item