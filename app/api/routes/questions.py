from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.student_question import StudentQuestionCreate, StudentQuestionResponse
from app.schemas.ai_answer import AIAnswerCreate, AIAnswerResponse
from app.schemas.teacher_answer import TeacherAnswerCreate, TeacherAnswerResponse
from app.crud.question import student_question, ai_answer, teacher_answer
from app.core.security import get_current_user, require_roles
from app.core.config import settings
from app.core.premium import require_premium_access
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.models.level import Level
from app.models.subject import Subject
from app.models.student_question import StudentQuestion
from app.models.ai_answer import AIAnswer
from app.models.teacher_answer import TeacherAnswer
from app.services.ai_service import ask_ai
from app.services.gamification_service import award_points
from app.services.question_notifications import (
    notify_subject_teachers_question_available,
    notify_teacher_question_assigned,
)

XP_ASK_QUESTION = 5

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]
TEACHER_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR", "ENSEIGNANT"]
STUDENT_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR", "ELEVE"]


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


def serialize_subject(subject: Subject | None):
    if not subject:
        return None
    return {"id": subject.id, "name_fr": subject.name_fr, "name_en": subject.name_en}


def serialize_level(level: Level | None):
    if not level:
        return None
    return {"id": level.id, "name_fr": level.name_fr, "name_en": level.name_en}


def serialize_ai_answer(answer: AIAnswer):
    return {
        "id": answer.id,
        "question_id": answer.question_id,
        "answer_text": answer.answer_text,
        "language": answer.language,
        "confidence_score": float(answer.confidence_score) if answer.confidence_score is not None else None,
        "model_used": answer.model_used,
        "sources_used": answer.sources_used,
        "response_type": answer.response_type,
        "created_at": answer.created_at,
    }


def serialize_teacher_answer(answer: TeacherAnswer):
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


def teacher_can_access_question(db: Session, user: User, question) -> bool:
    if user.role in ADMIN_ROLES:
        return True
    if user.role != "ENSEIGNANT":
        return False
    if question.assigned_teacher_id == user.id:
        return True
    if not question.subject_id:
        return False
    return (
        db.query(TeacherSubject)
        .filter(
            TeacherSubject.teacher_id == user.id,
            TeacherSubject.subject_id == question.subject_id,
        )
        .first()
        is not None
    )


def ensure_question_access(db: Session, user: User, question):
    if user.role == "ELEVE" and question.student_id != user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez consulter que vos propres questions")
    if user.role == "ENSEIGNANT" and not teacher_can_access_question(db, user, question):
        raise HTTPException(status_code=403, detail="Vous ne pouvez consulter que les questions de vos matières")
    if user.role == "ENSEIGNANT_EN_ATTENTE":
        raise HTTPException(status_code=403, detail="Compte enseignant en attente de validation")


def serialize_question_detail(db: Session, question, current_user: User):
    ai_answers = (
        db.query(AIAnswer)
        .filter(AIAnswer.question_id == question.id)
        .order_by(AIAnswer.created_at.desc())
        .all()
    )
    teacher_answers_query = (
        db.query(TeacherAnswer)
        .filter(TeacherAnswer.question_id == question.id)
        .order_by(TeacherAnswer.created_at.desc())
    )
    if current_user.role == "ELEVE":
        teacher_answers_query = teacher_answers_query.filter(TeacherAnswer.status == "PUBLISHED")
    teacher_answers = teacher_answers_query.all()
    latest_teacher_answer = teacher_answers[0] if teacher_answers else None
    latest_ai_answer = ai_answers[0] if ai_answers else None

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
        "answered_at": question.answered_at,
        "created_offline": question.created_offline,
        "local_temp_id": question.local_temp_id,
        "sync_status": question.sync_status,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "subject": serialize_subject(question.subject),
        "level": serialize_level(question.level),
        "student": serialize_user(question.student),
        "assigned_teacher": serialize_user(question.assigned_teacher),
        "ai_answers": [serialize_ai_answer(answer) for answer in ai_answers],
        "teacher_answers": [serialize_teacher_answer(answer) for answer in teacher_answers],
        "ai_answer": serialize_ai_answer(latest_ai_answer) if latest_ai_answer else None,
        "teacher_answer": serialize_teacher_answer(latest_teacher_answer) if latest_teacher_answer else None,
        "has_ai_answer": bool(ai_answers),
        "has_teacher_answer": bool(teacher_answers),
    }


def create_student_question_in_transaction(db: Session, payload: StudentQuestionCreate) -> StudentQuestion:
    obj_data = payload.model_dump(exclude={"answer_mode", "requested_teacher_id"})
    question = StudentQuestion(**obj_data)
    db.add(question)
    db.flush()
    return question


@router.post("/", response_model=StudentQuestionResponse)
def create_question(
    payload: StudentQuestionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(STUDENT_ROLES)),
):
    if current_user.role == "ELEVE":
        if not current_user.level_id:
            raise HTTPException(
                status_code=400,
                detail="Avant de poser une question, choisissez votre niveau scolaire pour recevoir une réponse adaptée.",
            )
        payload.student_id = current_user.id
        payload.level_id = current_user.level_id

    answer_mode = (payload.answer_mode or "TEACHER").upper()

    if answer_mode not in {"AI", "TEACHER"}:
        raise HTTPException(status_code=400, detail="Mode de réponse invalide")

    if answer_mode == "AI":
        if current_user.role == "ELEVE":
            require_premium_access(db, current_user.id)

        question = create_student_question_in_transaction(db, payload)

        try:
            subject = db.query(Subject).filter(Subject.id == payload.subject_id).first() if payload.subject_id else None
            level = db.query(Level).filter(Level.id == payload.level_id).first() if payload.level_id else None
            answer_text = ask_ai(
                payload.question_text or "",
                subject_name=subject.name_fr if subject else None,
                level_name=level.name_fr if level else None,
                language=payload.language,
                mode="STUDENT_QUESTION",
            )
        except HTTPException:
            question.status = "REQUESTED_TEACHER"
            question.teacher_requested = True
            notify_subject_teachers_question_available(
                db,
                question=question,
                background_tasks=background_tasks,
            )
            db.commit()
            db.refresh(question)
            return question

        db.add(
            AIAnswer(
                question_id=question.id,
                answer_text=answer_text,
                confidence_score=80.0,
                language=payload.language,
                model_used=settings.OPENAI_MODEL,
                sources_used={"kouma_ia": True},
            )
        )

        question.status = "ANSWERED_BY_AI"
        db.commit()
        db.refresh(question)
        if current_user.role == "ELEVE":
            award_points(db, current_user.id, XP_ASK_QUESTION)
        return question

    requested_teacher = None
    if payload.requested_teacher_id:
        requested_teacher = (
            db.query(User)
            .join(TeacherSubject, TeacherSubject.teacher_id == User.id)
            .filter(
                User.id == payload.requested_teacher_id,
                User.role == "ENSEIGNANT",
                TeacherSubject.subject_id == payload.subject_id,
            )
            .first()
        )

        if not requested_teacher:
            raise HTTPException(
                status_code=400,
                detail="Enseignant indisponible pour cette matière",
            )

    question = create_student_question_in_transaction(db, payload)
    question.teacher_requested = True
    question.status = "REQUESTED_TEACHER"

    if requested_teacher:
        question.assigned_teacher_id = requested_teacher.id
        question.status = "ASSIGNED_TO_TEACHER"
        notify_teacher_question_assigned(
            db,
            question=question,
            teacher=requested_teacher,
            background_tasks=background_tasks,
        )
    else:
        notify_subject_teachers_question_available(
            db,
            question=question,
            background_tasks=background_tasks,
        )

    db.commit()
    db.refresh(question)
    if current_user.role == "ELEVE":
        award_points(db, current_user.id, XP_ASK_QUESTION)
    return question


@router.get("/", response_model=list[StudentQuestionResponse])
def get_questions(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return student_question.get_all(db)


@router.get("/me")
def get_my_questions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    questions = student_question.get_by_student(db, current_user.id)
    return [serialize_question_detail(db, question, current_user) for question in questions]


@router.get("/student/{student_id}", response_model=list[StudentQuestionResponse])
def get_student_questions(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return student_question.get_by_student(db, student_id)


@router.get("/pending-teacher", response_model=list[StudentQuestionResponse])
def get_pending_teacher_questions(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(TEACHER_ROLES)),
):
    return student_question.get_pending_teacher_questions(db)


@router.post("/{question_id}/request-teacher", response_model=StudentQuestionResponse)
def request_teacher_answer(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(STUDENT_ROLES)),
):
    question = student_question.get(db, question_id)

    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    if current_user.role == "ELEVE" and question.student_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez demander un enseignant que pour vos propres questions",
        )

    return student_question.request_teacher(db, question_id)


@router.post("/ai-answers", response_model=AIAnswerResponse)
def create_ai_answer(
    payload: AIAnswerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return ai_answer.create(db, payload)


@router.post("/teacher-answers", response_model=TeacherAnswerResponse)
def create_teacher_answer(
    payload: TeacherAnswerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(TEACHER_ROLES)),
):
    if current_user.role == "ENSEIGNANT":
        payload.teacher_id = current_user.id

    return teacher_answer.create(db, payload)


@router.get("/{question_id}")
def get_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_question = student_question.get(db, question_id)

    if not db_question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    ensure_question_access(db, current_user, db_question)

    return serialize_question_detail(db, db_question, current_user)


@router.put("/{question_id}", response_model=StudentQuestionResponse)
def update_question(
    question_id: UUID,
    payload: StudentQuestionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_question = student_question.get(db, question_id)

    if not db_question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    if current_user.role == "ELEVE" and db_question.student_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez modifier que vos propres questions",
        )

    if current_user.role == "ENSEIGNANT":
        raise HTTPException(
            status_code=403,
            detail="Un enseignant ne peut pas modifier une question élève",
        )

    if current_user.role == "ELEVE":
        payload.student_id = current_user.id

    return student_question.update(db, db_question, payload)


@router.delete("/{question_id}", response_model=StudentQuestionResponse)
def delete_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_question = student_question.get(db, question_id)

    if not db_question:
        raise HTTPException(status_code=404, detail="Question introuvable")

    if current_user.role == "ELEVE" and db_question.student_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez supprimer que vos propres questions",
        )

    if current_user.role == "ENSEIGNANT":
        raise HTTPException(
            status_code=403,
            detail="Un enseignant ne peut pas supprimer une question élève",
        )

    return student_question.delete(db, question_id)
