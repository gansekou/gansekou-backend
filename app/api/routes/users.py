from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.subject import Subject
from app.models.teacher_subject import TeacherSubject
from app.schemas.user import (
    GANSEKOU_ROLES,
    AdminRoleUpdate,
    TeacherApplicationCreate,
    TeacherApplicationResponse,
    UserCreate,
    UserProfileUpdate,
    UserResponse,
    UserUpdate,
)
from app.crud.user import user
from app.core.security import get_current_user, require_roles

router = APIRouter()
ADMIN_ROLE_LIST = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]


@router.post("/", response_model=UserResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"])),
):
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=400, detail="Email ou téléphone obligatoire")

    existing = user.get_by_firebase_uid(db, payload.firebase_uid)
    if existing:
        raise HTTPException(status_code=400, detail="Utilisateur déjà existant")

    return user.create_user(db, payload)


@router.get("/me/profile", response_model=UserResponse)
def get_my_profile(current_user=Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return user.update(db, current_user, payload)


@router.patch("/me/profile", response_model=UserResponse)
def update_my_profile_completion(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return user.update(db, current_user, payload)


@router.post("/me/teacher-application", response_model=TeacherApplicationResponse)
def submit_teacher_application(
    payload: TeacherApplicationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not payload.subject_ids:
        raise HTTPException(status_code=400, detail="Au moins une matiÃ¨re est obligatoire")

    if not payload.proof_url:
        raise HTTPException(status_code=400, detail="Justificatif enseignant obligatoire")

    subjects = db.query(Subject).filter(Subject.id.in_(payload.subject_ids)).all()
    if len(subjects) != len(set(payload.subject_ids)):
        raise HTTPException(status_code=404, detail="Une ou plusieurs matiÃ¨res sont introuvables")

    db.query(TeacherSubject).filter(TeacherSubject.teacher_id == current_user.id).delete()
    links = [
        TeacherSubject(teacher_id=current_user.id, subject_id=subject.id)
        for subject in subjects
    ]
    for link in links:
        db.add(link)

    current_user.proof_url = payload.proof_url
    current_user.role = "ENSEIGNANT_EN_ATTENTE"

    db.commit()
    db.refresh(current_user)
    for link in links:
        db.refresh(link)

    return {
        "user": current_user,
        "teacher_subjects": [
            {
                "id": link.id,
                "teacher_id": link.teacher_id,
                "subject_id": link.subject_id,
                "created_at": link.created_at,
            }
            for link in links
        ],
    }


@router.get("/", response_model=list[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLE_LIST)),
):
    return user.get_all(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLE_LIST)),
):
    db_user = user.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLE_LIST)),
):
    db_user = user.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if db_user.role == "PROMOTEUR" and current_user.role != "PROMOTEUR":
        raise HTTPException(
            status_code=403,
            detail="Seul le promoteur peut modifier un promoteur",
        )

    return user.update(db, db_user, payload)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    payload: AdminRoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLE_LIST)),
):
    next_role = payload.role.strip().upper()
    if next_role not in GANSEKOU_ROLES:
        raise HTTPException(status_code=400, detail="RÃ´le invalide")

    db_user = user.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if db_user.role == "PROMOTEUR" and current_user.role != "PROMOTEUR":
        raise HTTPException(status_code=403, detail="Seul le promoteur peut modifier un promoteur")

    if next_role == "PROMOTEUR" and current_user.role != "PROMOTEUR":
        raise HTTPException(status_code=403, detail="Seul le promoteur peut nommer un promoteur")

    db_user.role = next_role
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["PROMOTEUR"])),
):
    db_user = user.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas supprimer votre propre compte promoteur ici",
        )

    return user.delete(db, user_id)
