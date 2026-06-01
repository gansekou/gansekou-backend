import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database.session import get_db
from app.models.user import User
from app.models.student_question import StudentQuestion
from app.models.teacher_subject import TeacherSubject
from app.models.teacher_answer import TeacherAnswer
from app.core.security import get_current_user
from app.services.question_notifications import notify_student_teacher_answered, notify_teacher_question_assigned
from app.services.teacher_xp_service import XP_ANSWER_QUESTION, award_teacher_xp

router = APIRouter()


class TeacherAnswerPayload(BaseModel):
    answer_text: str
    attachment_url: str | None = None
    language: str = "FR"


def serialize_question(question: StudentQuestion):
    return {
        "id": question.id,
        "student_id": question.student_id,
        "subject_id": question.subject_id,
        "level_id": question.level_id,
        "question_text": question.question_text,
        "question_image_url": question.question_image_url,
        "language": question.language,
        "status": question.status,
        "teacher_requested": question.teacher_requested,
        "assigned_teacher_id": question.assigned_teacher_id,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "level": {
            "id": question.level.id,
            "name_fr": question.level.name_fr,
            "name_en": question.level.name_en,
        } if question.level else None,
        "subject": {
            "id": question.subject.id,
            "name_fr": question.subject.name_fr,
            "name_en": question.subject.name_en,
        } if question.subject else None,
    }


@router.get("/pending")
def get_pending_teacher_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ENSEIGNANT":
        raise HTTPException(status_code=403, detail="AccÃ¨s rÃ©servÃ© aux enseignants")

    teacher_subjects = (
        db.query(TeacherSubject)
        .filter(TeacherSubject.teacher_id == current_user.id)
        .all()
    )

    subject_ids = [ts.subject_id for ts in teacher_subjects]

    if not subject_ids:
        return []

    questions = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.teacher_requested == True,
            StudentQuestion.status == "REQUESTED_TEACHER",
            StudentQuestion.assigned_teacher_id.is_(None),
            StudentQuestion.subject_id.in_(subject_ids),
        )
        .order_by(StudentQuestion.created_at.desc())
        .all()
    )

    return questions


@router.get("/available")
def get_available_teacher_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ENSEIGNANT":
        raise HTTPException(status_code=403, detail="AccÃ¨s rÃ©servÃ© aux enseignants validÃ©s")

    teacher_subjects = (
        db.query(TeacherSubject)
        .filter(TeacherSubject.teacher_id == current_user.id)
        .all()
    )
    subject_ids = [item.subject_id for item in teacher_subjects]

    if not subject_ids:
        return []

    questions = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.subject_id.in_(subject_ids),
            StudentQuestion.status.in_(["REQUESTED_TEACHER", "ASSIGNED_TO_TEACHER"]),
            (
                StudentQuestion.assigned_teacher_id.is_(None)
                | (StudentQuestion.assigned_teacher_id == current_user.id)
            ),
        )
        .order_by(StudentQuestion.created_at.desc())
        .all()
    )

    return [serialize_question(question) for question in questions]


@router.post("/{question_id}/take")
def take_teacher_question(
    question_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ENSEIGNANT":
        raise HTTPException(status_code=403, detail="AccÃ¨s rÃ©servÃ© aux enseignants")

    question = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    if question.status != "REQUESTED_TEACHER":
        raise HTTPException(status_code=400, detail="Cette question n'est plus disponible")

    teacher_subject = (
        db.query(TeacherSubject)
        .filter(
            TeacherSubject.teacher_id == current_user.id,
            TeacherSubject.subject_id == question.subject_id,
        )
        .first()
    )

    if not teacher_subject:
        raise HTTPException(
            status_code=403,
            detail="Vous n'Ãªtes pas autorisÃ© Ã  traiter cette matiÃ¨re"
        )

    question.status = "ASSIGNED_TO_TEACHER"
    question.assigned_teacher_id = current_user.id
    notify_teacher_question_assigned(
        db,
        question=question,
        teacher=current_user,
        background_tasks=background_tasks,
    )

    db.commit()
    db.refresh(question)

    return {
        "message": "Question prise avec succÃ¨s",
        "question_id": question.id,
        "assigned_teacher_id": current_user.id,
        "status": question.status,
    }


@router.post("/{question_id}/answer")
def answer_teacher_question(
    question_id: uuid.UUID,
    payload: TeacherAnswerPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ENSEIGNANT":
        raise HTTPException(status_code=403, detail="AccÃ¨s rÃ©servÃ© aux enseignants")

    question = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    if question.status != "ASSIGNED_TO_TEACHER":
        raise HTTPException(
            status_code=400,
            detail="Cette question n'est pas assignÃ©e Ã  un enseignant"
        )

    if question.assigned_teacher_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Cette question est dÃ©jÃ  prise par un autre enseignant"
        )

    existing_answer = (
        db.query(TeacherAnswer)
        .filter(TeacherAnswer.question_id == question.id)
        .first()
    )

    if existing_answer:
        raise HTTPException(
            status_code=400,
            detail="Cette question a dÃ©jÃ  reÃ§u une rÃ©ponse"
        )

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

    return {
        "message": "RÃ©ponse envoyÃ©e avec succÃ¨s",
        "answer_id": answer.id,
        "question_id": question.id,
        "status": question.status,
    }

@router.get("/assigned")
def get_assigned_teacher_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ENSEIGNANT":
        raise HTTPException(
            status_code=403,
            detail="AccÃ¨s rÃ©servÃ© aux enseignants"
        )

    questions = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.assigned_teacher_id == current_user.id,
            StudentQuestion.status == "ASSIGNED_TO_TEACHER",
        )
        .order_by(StudentQuestion.created_at.desc())
        .all()
    )

    return questions

