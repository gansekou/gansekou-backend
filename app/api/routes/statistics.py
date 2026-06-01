from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.models.ai_answer import AIAnswer
from app.models.content import Content
from app.models.content_progress import ContentProgress
from app.models.level import Level
from app.models.payment_transaction import PaymentTransaction
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.student_gamification import StudentGamification
from app.models.student_question import StudentQuestion
from app.models.subject import Subject
from app.models.teacher_answer import TeacherAnswer
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.services.gamification_service import get_or_create_profile, level_label

router = APIRouter()

ADMIN_ROLES = {"ADMIN", "PROMOTEUR", "ADMINISTRATEUR"}


def require_admin(user: User):
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration")


def since(days: int):
    return datetime.now(timezone.utc) - timedelta(days=days)


def percent(value: int | float, total: int | float) -> float:
    return round((value / total) * 100, 2) if total else 0


def series_for_last_days(db: Session, model, date_column, days: int = 14, filters=()):
    start = since(days - 1)
    rows = (
        db.query(func.date(date_column).label("day"), func.count(model.id))
        .filter(date_column >= start, *filters)
        .group_by(func.date(date_column))
        .all()
    )
    by_day = {str(day): count for day, count in rows}

    return [
        {
            "label": (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat(),
            "value": by_day.get(str((datetime.now(timezone.utc) - timedelta(days=offset)).date()), 0),
        }
        for offset in reversed(range(days))
    ]


def content_summary(item: Content | None):
    if not item:
        return None

    return {
        "id": item.id,
        "title": item.title,
        "views": item.total_views,
        "downloads": item.total_downloads,
    }


def quiz_summary(item: Quiz | None):
    if not item:
        return None

    return {
        "id": item.id,
        "title": item.title,
        "attempts": item.total_attempts,
    }


@router.get("/admin/overview")
def admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    today = since(1)
    month = since(30)

    total_users = db.query(User).count()
    active_today = (
        db.query(User)
        .filter(User.updated_at >= today)
        .count()
    )
    new_students = db.query(User).filter(User.role == "ELEVE", User.created_at >= month).count()
    new_teachers = db.query(User).filter(User.role == "ENSEIGNANT", User.created_at >= month).count()
    pending_teachers = db.query(User).filter(User.role == "ENSEIGNANT_EN_ATTENTE").count()
    contents_published = db.query(Content).filter(Content.status == "APPROVED").count()
    contents_premium = db.query(Content).filter(Content.is_premium == True).count()
    quizzes_created = db.query(Quiz).count()
    quiz_completed = db.query(QuizAttempt).filter(QuizAttempt.completed_at.isnot(None)).count()
    questions_ai = db.query(StudentQuestion).filter(StudentQuestion.status == "ANSWERED_BY_AI").count()
    questions_teacher = db.query(StudentQuestion).filter(StudentQuestion.teacher_requested == True).count()
    successful_payments = db.query(PaymentTransaction).filter(PaymentTransaction.status == "SUCCESS")
    revenue_total = successful_payments.with_entities(func.coalesce(func.sum(PaymentTransaction.amount_xaf), 0)).scalar()
    revenue_month = successful_payments.filter(PaymentTransaction.updated_at >= month).with_entities(func.coalesce(func.sum(PaymentTransaction.amount_xaf), 0)).scalar()
    started_contents = db.query(ContentProgress).count()
    completed_contents = db.query(ContentProgress).filter(ContentProgress.is_completed == True).count()

    top_subjects = (
        db.query(Subject.id, Subject.name_fr, Subject.name_en, func.count(StudentQuestion.id).label("total"))
        .join(StudentQuestion, StudentQuestion.subject_id == Subject.id)
        .group_by(Subject.id, Subject.name_fr, Subject.name_en)
        .order_by(desc("total"))
        .limit(8)
        .all()
    )
    top_levels = (
        db.query(Level.id, Level.name_fr, Level.name_en, func.count(User.id).label("total"))
        .join(User, User.level_id == Level.id)
        .group_by(Level.id, Level.name_fr, Level.name_en)
        .order_by(desc("total"))
        .limit(8)
        .all()
    )
    top_teachers = (
        db.query(User.id, User.nom, User.prenom, func.count(TeacherAnswer.id).label("answers"))
        .join(TeacherAnswer, TeacherAnswer.teacher_id == User.id)
        .group_by(User.id)
        .order_by(desc("answers"))
        .limit(8)
        .all()
    )
    top_contents = (
        db.query(Content.id, Content.title, Content.total_views, Content.total_downloads)
        .order_by(Content.total_views.desc())
        .limit(8)
        .all()
    )
    top_quizzes = (
        db.query(Quiz.id, Quiz.title, Quiz.total_attempts)
        .order_by(Quiz.total_attempts.desc())
        .limit(8)
        .all()
    )

    return {
        "metrics": {
            "total_users": total_users,
            "active_today": active_today,
            "growth_users_30d": db.query(User).filter(User.created_at >= month).count(),
            "new_students_30d": new_students,
            "new_teachers_30d": new_teachers,
            "pending_teachers": pending_teachers,
            "contents_published": contents_published,
            "contents_premium": contents_premium,
            "quizzes_created": quizzes_created,
            "quiz_completed": quiz_completed,
            "questions_ai": questions_ai,
            "questions_teacher": questions_teacher,
            "revenue_total_xaf": int(revenue_total or 0),
            "revenue_month_xaf": int(revenue_month or 0),
            "engagement_rate": percent(active_today, total_users),
            "quiz_completion_rate": percent(quiz_completed, max(db.query(QuizAttempt).count(), 1)),
            "content_completion_rate": percent(completed_contents, max(started_contents, 1)),
        },
        "charts": {
            "users_growth": series_for_last_days(db, User, User.created_at, 14),
            "questions": series_for_last_days(db, StudentQuestion, StudentQuestion.created_at, 14),
            "quiz_attempts": series_for_last_days(db, QuizAttempt, QuizAttempt.started_at, 14),
            "revenue": series_for_last_days(db, PaymentTransaction, PaymentTransaction.updated_at, 14, (PaymentTransaction.status == "SUCCESS",)),
        },
        "tops": {
            "subjects": [{"id": row.id, "name_fr": row.name_fr, "name_en": row.name_en, "value": row.total} for row in top_subjects],
            "levels": [{"id": row.id, "name_fr": row.name_fr, "name_en": row.name_en, "value": row.total} for row in top_levels],
            "teachers": [{"id": row.id, "name": f"{row.prenom} {row.nom}", "value": row.answers} for row in top_teachers],
            "contents": [{"id": row.id, "title": row.title, "views": row.total_views, "downloads": row.total_downloads} for row in top_contents],
            "quizzes": [{"id": row.id, "title": row.title, "value": row.total_attempts} for row in top_quizzes],
        },
    }


@router.get("/teacher/overview")
def teacher_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ENSEIGNANT":
        raise HTTPException(status_code=403, detail="Accès réservé aux enseignants validés")

    subject_ids = [
        row.subject_id
        for row in db.query(TeacherSubject).filter(TeacherSubject.teacher_id == current_user.id).all()
    ]
    profile = get_or_create_profile(db, current_user.id)
    contents = db.query(Content).filter(Content.author_id == current_user.id).all()
    answers = db.query(TeacherAnswer).filter(TeacherAnswer.teacher_id == current_user.id).count()
    pending = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.status == "REQUESTED_TEACHER", StudentQuestion.subject_id.in_(subject_ids))
        .count()
        if subject_ids else 0
    )
    views = sum(item.total_views or 0 for item in contents)
    downloads = sum(item.total_downloads or 0 for item in contents)
    quizzes = db.query(Quiz).filter(Quiz.author_id == current_user.id).all()

    return {
        "metrics": {
            "xp": profile.points,
            "level": profile.level,
            "level_label": level_label(profile.points, current_user.role),
            "rank": 1 + db.query(StudentGamification).filter(StudentGamification.points > profile.points).count(),
            "subjects": len(subject_ids),
            "pending_questions": pending,
            "answered_questions": answers,
            "response_rate": percent(answers, answers + pending),
            "content_views": views,
            "content_downloads": downloads,
            "contents": len(contents),
            "quizzes": len(quizzes),
            "potential_revenue_xaf": views * 5 + downloads * 10,
        },
        "charts": {
            "xp": series_for_last_days(db, TeacherAnswer, TeacherAnswer.created_at, 14, (TeacherAnswer.teacher_id == current_user.id,)),
            "answers": series_for_last_days(db, TeacherAnswer, TeacherAnswer.created_at, 14, (TeacherAnswer.teacher_id == current_user.id,)),
            "content_views": [{"label": item.title or str(item.id)[:8], "value": item.total_views or 0} for item in contents[:8]],
        },
        "highlights": {
            "top_content": content_summary(max(contents, key=lambda item: item.total_views or 0, default=None)),
            "top_quiz": quiz_summary(max(quizzes, key=lambda item: item.total_attempts or 0, default=None)),
        },
    }


@router.get("/student/overview")
def student_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ELEVE":
        raise HTTPException(status_code=403, detail="Accès réservé aux élèves")

    profile = get_or_create_profile(db, current_user.id)
    progress = db.query(ContentProgress).filter(ContentProgress.student_id == current_user.id).all()
    attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == current_user.id).order_by(QuizAttempt.started_at.desc()).all()
    questions = db.query(StudentQuestion).filter(StudentQuestion.student_id == current_user.id).count()
    completed = len([item for item in progress if item.is_completed])
    total_time = sum(item.time_spent_minutes or 0 for item in progress)

    return {
        "metrics": {
            "xp": profile.points,
            "level": profile.level,
            "level_label": level_label(profile.points, current_user.role),
            "streak": profile.current_streak_days,
            "best_streak": profile.best_streak_days,
            "contents_started": len(progress),
            "contents_completed": completed,
            "content_completion_rate": percent(completed, len(progress)),
            "quizzes_completed": profile.quizzes_completed,
            "quizzes_passed": profile.quizzes_passed,
            "questions_asked": questions,
            "learning_time_minutes": total_time,
            "rank": 1 + db.query(StudentGamification).filter(StudentGamification.points > profile.points).count(),
        },
        "charts": {
            "progress": [{"label": str(item.content_id)[:8], "value": item.progress_percent or 0} for item in progress[:10]],
            "scores": [{"label": item.started_at.date().isoformat(), "value": item.score} for item in attempts[:10]],
            "activity": series_for_last_days(db, QuizAttempt, QuizAttempt.started_at, 21, (QuizAttempt.student_id == current_user.id,)),
        },
        "recent_quizzes": [
            {"id": item.id, "quiz_id": item.quiz_id, "score": item.score, "is_passed": item.is_passed, "started_at": item.started_at}
            for item in attempts[:8]
        ],
    }


@router.get("/leaderboards")
def leaderboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    learners = (
        db.query(StudentGamification, User)
        .join(User, User.id == StudentGamification.student_id)
        .filter(User.role == "ELEVE")
        .order_by(StudentGamification.points.desc())
        .limit(50)
        .all()
    )
    teachers = (
        db.query(StudentGamification, User)
        .join(User, User.id == StudentGamification.student_id)
        .filter(User.role == "ENSEIGNANT")
        .order_by(StudentGamification.points.desc())
        .limit(50)
        .all()
    )

    def row(profile, user):
        return {
            "user_id": user.id,
            "name": f"{user.prenom} {user.nom}",
            "role": user.role,
            "points": profile.points,
            "level": profile.level,
            "level_label": level_label(profile.points, user.role),
        }

    return {
        "learners": [row(profile, user) for profile, user in learners],
        "teachers": [row(profile, user) for profile, user in teachers],
    }
