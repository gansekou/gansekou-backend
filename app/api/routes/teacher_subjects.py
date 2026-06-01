import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.subject import Subject
from app.models.teacher_subject import TeacherSubject
from app.core.security import get_current_user

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]
TEACHER_PROFILE_ROLES = ["ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"]


class TeacherSubjectBulkUpdate(BaseModel):
    subject_ids: list[uuid.UUID]


def require_admin(current_user: User):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administrateur")


@router.post("/{teacher_id}/{subject_id}")
def assign_subject_to_teacher(
    teacher_id: uuid.UUID,
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    teacher = db.query(User).filter(User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Enseignant introuvable")

    if teacher.role not in TEACHER_PROFILE_ROLES:
        raise HTTPException(status_code=400, detail="Cet utilisateur n'est pas un enseignant")

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Matière introuvable")

    existing = (
        db.query(TeacherSubject)
        .filter(
            TeacherSubject.teacher_id == teacher_id,
            TeacherSubject.subject_id == subject_id,
        )
        .first()
    )

    if existing:
        return {
            "message": "Cette matière est déjà affectée à cet enseignant",
            "teacher_subject_id": existing.id,
        }

    teacher_subject = TeacherSubject(
        teacher_id=teacher_id,
        subject_id=subject_id,
    )

    db.add(teacher_subject)
    db.commit()
    db.refresh(teacher_subject)

    return {
        "message": "Matière affectée à l'enseignant avec succès",
        "teacher_subject_id": teacher_subject.id,
        "teacher_id": teacher_id,
        "subject_id": subject_id,
    }


@router.put("/me")
def update_my_teacher_subjects(
    payload: TeacherSubjectBulkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in TEACHER_PROFILE_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé aux enseignants")

    requested_ids = set(payload.subject_ids)
    valid_subjects = db.query(Subject).filter(Subject.id.in_(requested_ids)).all()
    valid_subject_ids = {subject.id for subject in valid_subjects}

    if len(valid_subject_ids) != len(requested_ids):
        raise HTTPException(status_code=400, detail="Une ou plusieurs matières sont invalides")

    db.query(TeacherSubject).filter(
        TeacherSubject.teacher_id == current_user.id
    ).delete()

    for subject_id in valid_subject_ids:
        db.add(TeacherSubject(teacher_id=current_user.id, subject_id=subject_id))

    db.commit()

    return (
        db.query(TeacherSubject)
        .filter(TeacherSubject.teacher_id == current_user.id)
        .all()
    )


@router.get("/teachers/by-subject/{subject_id}")
def get_validated_teachers_by_subject(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Matière introuvable")

    teachers = (
        db.query(User)
        .join(TeacherSubject, TeacherSubject.teacher_id == User.id)
        .filter(
            TeacherSubject.subject_id == subject_id,
            User.role == "ENSEIGNANT",
            User.status == "ACTIVE",
        )
        .order_by(User.nom.asc(), User.prenom.asc())
        .all()
    )

    return [
        {
            "id": teacher.id,
            "nom": teacher.nom,
            "prenom": teacher.prenom,
            "profile_url": teacher.profile_url,
            "role": teacher.role,
            "subject_id": subject_id,
        }
        for teacher in teachers
    ]


@router.get("/teacher/{teacher_id}")
def get_teacher_subjects(
    teacher_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != teacher_id:
        require_admin(current_user)

    teacher = db.query(User).filter(User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Enseignant introuvable")

    subjects = (
        db.query(TeacherSubject)
        .filter(TeacherSubject.teacher_id == teacher_id)
        .all()
    )

    return subjects


@router.get("/me")
def get_my_teacher_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in TEACHER_PROFILE_ROLES:
        raise HTTPException(status_code=403, detail="AccÃ¨s rÃ©servÃ© aux enseignants")

    return (
        db.query(TeacherSubject)
        .filter(TeacherSubject.teacher_id == current_user.id)
        .all()
    )


@router.delete("/{teacher_subject_id}")
def remove_subject_from_teacher(
    teacher_subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher_subject = (
        db.query(TeacherSubject)
        .filter(TeacherSubject.id == teacher_subject_id)
        .first()
    )

    if not teacher_subject:
        raise HTTPException(status_code=404, detail="Affectation introuvable")

    if current_user.id != teacher_subject.teacher_id:
        require_admin(current_user)
    elif current_user.role not in TEACHER_PROFILE_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé aux enseignants")

    db.delete(teacher_subject)
    db.commit()

    return {
        "message": "Matière retirée de l'enseignant avec succès"
    }
