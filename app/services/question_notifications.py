from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.websocket_manager import websocket_manager
from app.models.notification import Notification
from app.models.student_question import StudentQuestion
from app.models.teacher_answer import TeacherAnswer
from app.models.teacher_subject import TeacherSubject
from app.models.user import User


def _language(value: str | None) -> str:
    return "EN" if value == "EN" else "FR"


def _add_notification(
    db: Session,
    *,
    user_id,
    title: str,
    message: str,
    language: str,
    type_: str,
    data: dict,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        language=language,
        type=type_,
        data=data,
    )
    db.add(notification)
    return notification


def queue_notification(background_tasks: BackgroundTasks | None, user_id, payload: dict):
    if background_tasks is not None:
        background_tasks.add_task(websocket_manager.send_to_user, user_id, payload)


def notify_student_teacher_answered(
    db: Session,
    *,
    question: StudentQuestion,
    answer: TeacherAnswer,
    teacher_id,
    background_tasks: BackgroundTasks | None = None,
) -> Notification:
    language = _language(question.language)
    title = "Your question has been answered" if language == "EN" else "Votre question a reçu une réponse"
    message = (
        "A teacher answered your question. You can view the answer now."
        if language == "EN"
        else "Un enseignant a répondu à votre question. Consultez la réponse maintenant."
    )
    data = {
        "question_id": str(question.id),
        "answer_id": str(answer.id),
        "teacher_id": str(teacher_id),
    }
    notification = _add_notification(
        db,
        user_id=question.student_id,
        title=title,
        message=message,
        language=language,
        type_="TEACHER_ANSWERED_QUESTION",
        data=data,
    )
    queue_notification(
        background_tasks,
        question.student_id,
        {"type": "TEACHER_ANSWERED_QUESTION", "title": title, "message": message, **data},
    )
    return notification


def notify_teacher_question_assigned(
    db: Session,
    *,
    question: StudentQuestion,
    teacher: User,
    background_tasks: BackgroundTasks | None = None,
) -> Notification:
    language = _language(getattr(teacher, "preferred_language", "FR"))
    title = "New assigned question" if language == "EN" else "Nouvelle question attribuée"
    message = (
        "A question related to your subject has been assigned to you."
        if language == "EN"
        else "Une question liée à votre matière vous a été attribuée."
    )
    data = {
        "question_id": str(question.id),
        "student_id": str(question.student_id),
        "subject_id": str(question.subject_id) if question.subject_id else None,
    }
    notification = _add_notification(
        db,
        user_id=teacher.id,
        title=title,
        message=message,
        language=language,
        type_="QUESTION_ASSIGNED_TO_TEACHER",
        data=data,
    )
    queue_notification(
        background_tasks,
        teacher.id,
        {"type": "QUESTION_ASSIGNED_TO_TEACHER", "title": title, "message": message, **data},
    )
    return notification


def notify_subject_teachers_question_available(
    db: Session,
    *,
    question: StudentQuestion,
    background_tasks: BackgroundTasks | None = None,
) -> list[Notification]:
    if not question.subject_id:
        return []

    teachers = (
        db.query(User)
        .join(TeacherSubject, TeacherSubject.teacher_id == User.id)
        .filter(
            User.role == "ENSEIGNANT",
            User.status == "ACTIVE",
            TeacherSubject.subject_id == question.subject_id,
        )
        .all()
    )

    notifications: list[Notification] = []
    for teacher in teachers:
        language = _language(getattr(teacher, "preferred_language", "FR"))
        title = "New question available" if language == "EN" else "Nouvelle question disponible"
        message = (
            "A student asked a question in one of your subjects."
            if language == "EN"
            else "Un élève a posé une question dans l’une de vos matières."
        )
        data = {
            "question_id": str(question.id),
            "student_id": str(question.student_id),
            "subject_id": str(question.subject_id),
        }
        notifications.append(
            _add_notification(
                db,
                user_id=teacher.id,
                title=title,
                message=message,
                language=language,
                type_="QUESTION_AVAILABLE_FOR_SUBJECT_TEACHERS",
                data=data,
            )
        )
        queue_notification(
            background_tasks,
            teacher.id,
            {"type": "QUESTION_AVAILABLE_FOR_SUBJECT_TEACHERS", "title": title, "message": message, **data},
        )
    return notifications
