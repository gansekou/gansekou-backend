import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.student_question import StudentQuestion
from app.models.teacher_answer import TeacherAnswer
from app.core.security import get_current_user

router = APIRouter()


def require_student(current_user: User):
    if current_user.role != "ELEVE":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux élèves"
        )


def format_answer(answer: TeacherAnswer | None):
    if not answer:
        return None

    return {
        "id": answer.id,
        "answer_text": answer.answer_text,
        "attachment_url": answer.attachment_url,
        "language": answer.language,
        "status": answer.status,
        "teacher_id": answer.teacher_id,
        "created_at": answer.created_at,
    }


def format_question_with_answer(
    question: StudentQuestion,
    answer: TeacherAnswer | None = None,
):
    return {
        "question_id": question.id,
        "question_text": question.question_text,
        "question_image_url": question.question_image_url,
        "question_status": question.status,
        "teacher_requested": question.teacher_requested,
        "subject_id": question.subject_id,
        "level_id": question.level_id,
        "language": question.language,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "answered_at": question.answered_at,
        "answer": format_answer(answer),
    }


@router.get("/question/{question_id}")
def get_teacher_answer_for_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    question = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question introuvable"
        )

    if question.student_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous n'êtes pas autorisé à voir cette réponse"
        )

    answer = (
        db.query(TeacherAnswer)
        .filter(
            TeacherAnswer.question_id == question.id,
            TeacherAnswer.status == "PUBLISHED",
        )
        .first()
    )

    if not answer:
        raise HTTPException(
            status_code=404,
            detail="Aucune réponse enseignant disponible pour cette question"
        )

    return format_question_with_answer(question, answer)


@router.get("/my-answers")
def get_my_teacher_answers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    results = (
        db.query(StudentQuestion, TeacherAnswer)
        .join(
            TeacherAnswer,
            TeacherAnswer.question_id == StudentQuestion.id
        )
        .filter(
            StudentQuestion.student_id == current_user.id,
            TeacherAnswer.status == "PUBLISHED",
        )
        .order_by(TeacherAnswer.created_at.desc())
        .all()
    )

    return [
        format_question_with_answer(question, answer)
        for question, answer in results
    ]


@router.get("/my-questions")
def get_my_questions_with_possible_answers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    questions = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.student_id == current_user.id)
        .order_by(StudentQuestion.created_at.desc())
        .all()
    )

    response = []

    for question in questions:
        answer = (
            db.query(TeacherAnswer)
            .filter(
                TeacherAnswer.question_id == question.id,
                TeacherAnswer.status == "PUBLISHED",
            )
            .first()
        )

        response.append(
            format_question_with_answer(question, answer)
        )

    return response


@router.get("/pending")
def get_my_pending_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    questions = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.student_id == current_user.id,
            StudentQuestion.status.in_([
                "PENDING_AI",
                "REQUESTED_TEACHER",
                "ASSIGNED_TO_TEACHER",
            ]),
        )
        .order_by(StudentQuestion.created_at.desc())
        .all()
    )

    return [
        format_question_with_answer(question)
        for question in questions
    ]


@router.get("/answered")
def get_my_answered_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    results = (
        db.query(StudentQuestion, TeacherAnswer)
        .join(
            TeacherAnswer,
            TeacherAnswer.question_id == StudentQuestion.id
        )
        .filter(
            StudentQuestion.student_id == current_user.id,
            StudentQuestion.status == "ANSWERED_BY_TEACHER",
            TeacherAnswer.status == "PUBLISHED",
        )
        .order_by(TeacherAnswer.created_at.desc())
        .all()
    )

    return [
        format_question_with_answer(question, answer)
        for question, answer in results
    ]


@router.get("/stats")
def get_my_answer_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    total_questions = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.student_id == current_user.id)
        .count()
    )

    pending_ai = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.student_id == current_user.id,
            StudentQuestion.status == "PENDING_AI",
        )
        .count()
    )

    requested_teacher = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.student_id == current_user.id,
            StudentQuestion.status == "REQUESTED_TEACHER",
        )
        .count()
    )

    assigned_to_teacher = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.student_id == current_user.id,
            StudentQuestion.status == "ASSIGNED_TO_TEACHER",
        )
        .count()
    )

    answered_by_teacher = (
        db.query(StudentQuestion)
        .filter(
            StudentQuestion.student_id == current_user.id,
            StudentQuestion.status == "ANSWERED_BY_TEACHER",
        )
        .count()
    )

    teacher_answers = (
        db.query(TeacherAnswer)
        .join(
            StudentQuestion,
            TeacherAnswer.question_id == StudentQuestion.id
        )
        .filter(
            StudentQuestion.student_id == current_user.id,
            TeacherAnswer.status == "PUBLISHED",
        )
        .count()
    )

    return {
        "total_questions": total_questions,
        "pending_ai": pending_ai,
        "requested_teacher": requested_teacher,
        "assigned_to_teacher": assigned_to_teacher,
        "answered_by_teacher": answered_by_teacher,
        "teacher_answers": teacher_answers,
    }