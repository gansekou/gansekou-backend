import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.security import get_current_user
from app.database.session import get_db
from app.models.student_question import StudentQuestion
from app.models.teacher_answer import TeacherAnswer
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.services.question_notifications import notify_student_teacher_answered
from app.services.teacher_xp_service import XP_ANSWER_QUESTION, award_teacher_xp

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]


class TeacherAnswerCreatePayload(BaseModel):
    question_id: uuid.UUID
    answer_text: str
    attachment_url: str | None = None
    language: str = "FR"


def serialize_user(user: User | None):
    if not user:
        return None
    return {
        "id": user.id,
        "nom": user.nom,
        "prenom": user.prenom,
        "profile_url": user.profile_url,
        "role": user.role,
    }


def serialize_answer(answer: TeacherAnswer):
    return {
        "id": answer.id,
        "question_id": answer.question_id,
        "teacher_id": answer.teacher_id,
        "teacher": serialize_user(answer.teacher),
        "answer_text": answer.answer_text,
        "attachment_url": answer.attachment_url,
        "language": answer.language,
        "status": answer.status,
        "created_at": answer.created_at,
    }


def teacher_has_subject(db: Session, teacher_id, subject_id) -> bool:
    if not subject_id:
        return False
    return (
        db.query(TeacherSubject)
        .filter(
            TeacherSubject.teacher_id == teacher_id,
            TeacherSubject.subject_id == subject_id,
        )
        .first()
        is not None
    )


def ensure_teacher_can_answer(db: Session, user: User, question: StudentQuestion):
    if user.role in ADMIN_ROLES:
        return
    if user.role != "ENSEIGNANT":
        raise HTTPException(status_code=403, detail="Accès réservé aux enseignants validés")
    if question.assigned_teacher_id and question.assigned_teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Cette question est assignée à un autre enseignant")
    if not teacher_has_subject(db, user.id, question.subject_id):
        raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à répondre pour cette matière")


@router.get("/question/{question_id}")
def get_answers_for_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = db.query(StudentQuestion).filter(StudentQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    if current_user.role == "ELEVE" and question.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez voir que vos propres réponses")
    if current_user.role == "ENSEIGNANT" and not (
        question.assigned_teacher_id == current_user.id
        or teacher_has_subject(db, current_user.id, question.subject_id)
    ):
        raise HTTPException(status_code=403, detail="Vous ne pouvez voir que les réponses de vos matières")
    if current_user.role == "ENSEIGNANT_EN_ATTENTE":
        raise HTTPException(status_code=403, detail="Compte enseignant en attente de validation")

    query = db.query(TeacherAnswer).filter(TeacherAnswer.question_id == question.id)
    if current_user.role == "ELEVE":
        query = query.filter(TeacherAnswer.status == "PUBLISHED")
    answers = query.order_by(TeacherAnswer.created_at.desc()).all()
    return [serialize_answer(answer) for answer in answers]


@router.post("/")
def create_teacher_answer(
    payload: TeacherAnswerCreatePayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = db.query(StudentQuestion).filter(StudentQuestion.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    ensure_teacher_can_answer(db, current_user, question)

    existing_answer = (
        db.query(TeacherAnswer)
        .filter(TeacherAnswer.question_id == question.id, TeacherAnswer.status == "PUBLISHED")
        .first()
    )
    if existing_answer:
        raise HTTPException(status_code=400, detail="Cette question a déjà reçu une réponse")

    if current_user.role == "ENSEIGNANT" and question.assigned_teacher_id is None:
        question.assigned_teacher_id = current_user.id

    answer = TeacherAnswer(
        question_id=question.id,
        teacher_id=current_user.id,
        answer_text=payload.answer_text,
        attachment_url=payload.attachment_url,
        language=payload.language,
        status="PUBLISHED",
    )
    question.status = "ANSWERED_BY_TEACHER"
    question.teacher_requested = False
    question.answered_at = func.now()

    db.add(answer)
    db.flush()
    notify_student_teacher_answered(
        db,
        question=question,
        answer=answer,
        teacher_id=current_user.id,
        background_tasks=background_tasks,
    )
    db.commit()
    award_teacher_xp(db, current_user.id, XP_ANSWER_QUESTION)
    db.refresh(answer)
    return serialize_answer(answer)
