from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.subject import Subject
from app.models.student_question import StudentQuestion
from app.models.ai_answer import AIAnswer
from app.models.teacher_answer import TeacherAnswer
from app.models.teacher_subject import TeacherSubject
from app.models.ai_cache import AICache
from app.models.ai_usage_log import AIUsageLog
from app.schemas.user import GANSEKOU_ROLES, AdminRoleUpdate

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]


def require_admin(current_user: User):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à l'administrateur"
        )


def percent(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


@router.get("/stats/global")
def get_global_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    total_users = db.query(User).count()
    total_students = db.query(User).filter(User.role == "ELEVE").count()
    total_teachers = db.query(User).filter(User.role == "ENSEIGNANT").count()
    total_admins = db.query(User).filter(User.role == "ADMIN").count()

    total_questions = db.query(StudentQuestion).count()
    total_ai_answers = db.query(AIAnswer).count()
    total_teacher_answers = db.query(TeacherAnswer).count()

    pending_ai = db.query(StudentQuestion).filter(StudentQuestion.status == "PENDING_AI").count()
    requested_teacher = db.query(StudentQuestion).filter(StudentQuestion.status == "REQUESTED_TEACHER").count()
    assigned_teacher = db.query(StudentQuestion).filter(StudentQuestion.status == "ASSIGNED_TO_TEACHER").count()
    answered_ai = db.query(StudentQuestion).filter(StudentQuestion.status == "ANSWERED_BY_AI").count()
    answered_teacher = db.query(StudentQuestion).filter(StudentQuestion.status == "ANSWERED_BY_TEACHER").count()

    return {
        "users": {
            "total": total_users,
            "students": total_students,
            "teachers": total_teachers,
            "admins": total_admins,
        },
        "questions": {
            "total": total_questions,
            "pending_ai": pending_ai,
            "requested_teacher": requested_teacher,
            "assigned_to_teacher": assigned_teacher,
            "answered_by_ai": answered_ai,
            "answered_by_teacher": answered_teacher,
        },
        "answers": {
            "ai_answers": total_ai_answers,
            "teacher_answers": total_teacher_answers,
        },
        "rates": {
            "ai_resolution_rate_percent": percent(answered_ai, total_questions),
            "teacher_resolution_rate_percent": percent(answered_teacher, total_questions),
            "teacher_fallback_rate_percent": percent(
                requested_teacher + assigned_teacher + answered_teacher,
                total_questions
            ),
        },
        "system": {
            "teacher_subject_links": db.query(TeacherSubject).count(),
            "ai_cache_items": db.query(AICache).count(),
            "ai_usage_logs": db.query(AIUsageLog).count(),
        }
    }


@router.get("/stats/ai")
def get_ai_admin_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    start_date = date.today() - timedelta(days=days)

    total_ai_answers = db.query(AIAnswer).count()
    total_cache_items = db.query(AICache).count()

    cache_hits_sum = db.query(func.coalesce(func.sum(AICache.hit_count), 0)).scalar()

    usage_requests_sum = (
        db.query(func.coalesce(func.sum(AIUsageLog.request_count), 0))
        .filter(AIUsageLog.usage_date >= start_date)
        .scalar()
    )

    answered_by_ai = db.query(StudentQuestion).filter(StudentQuestion.status == "ANSWERED_BY_AI").count()

    fallback_questions = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.status.in_([
            "REQUESTED_TEACHER",
            "ASSIGNED_TO_TEACHER",
            "ANSWERED_BY_TEACHER",
        ]))
        .count()
    )

    total_questions = db.query(StudentQuestion).count()

    models = (
        db.query(
            AIAnswer.model_used,
            func.count(AIAnswer.id).label("total")
        )
        .group_by(AIAnswer.model_used)
        .order_by(desc("total"))
        .all()
    )

    languages = (
        db.query(
            AIAnswer.language,
            func.count(AIAnswer.id).label("total")
        )
        .group_by(AIAnswer.language)
        .order_by(desc("total"))
        .all()
    )

    return {
        "period_days": days,
        "ai_answers": total_ai_answers,
        "usage_requests": usage_requests_sum,
        "cache": {
            "items": total_cache_items,
            "total_hits": cache_hits_sum,
            "estimated_cache_hit_rate_percent": percent(cache_hits_sum, cache_hits_sum + total_ai_answers),
        },
        "performance": {
            "answered_by_ai_questions": answered_by_ai,
            "fallback_to_teacher_questions": fallback_questions,
            "ai_success_rate_percent": percent(answered_by_ai, total_questions),
            "fallback_rate_percent": percent(fallback_questions, total_questions),
        },
        "models": [
            {"model": model or "UNKNOWN", "answers": total}
            for model, total in models
        ],
        "languages": [
            {"language": language or "UNKNOWN", "answers": total}
            for language, total in languages
        ],
    }


@router.get("/stats/teachers")
def get_teacher_admin_stats(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    total_teachers = db.query(User).filter(User.role == "ENSEIGNANT").count()
    active_teachers = (
        db.query(TeacherAnswer.teacher_id)
        .distinct()
        .count()
    )

    top_teachers = (
        db.query(
            User.id,
            User.nom,
            User.prenom,
            func.count(TeacherAnswer.id).label("answers_count")
        )
        .join(TeacherAnswer, TeacherAnswer.teacher_id == User.id)
        .filter(User.role == "ENSEIGNANT")
        .group_by(User.id, User.nom, User.prenom)
        .order_by(desc("answers_count"))
        .limit(limit)
        .all()
    )

    assigned_questions = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.status == "ASSIGNED_TO_TEACHER")
        .count()
    )

    answered_by_teacher = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.status == "ANSWERED_BY_TEACHER")
        .count()
    )

    waiting_teacher = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.status == "REQUESTED_TEACHER")
        .count()
    )

    return {
        "teachers": {
            "total": total_teachers,
            "active": active_teachers,
            "inactive": max(total_teachers - active_teachers, 0),
        },
        "questions": {
            "waiting_teacher": waiting_teacher,
            "assigned_to_teacher": assigned_questions,
            "answered_by_teacher": answered_by_teacher,
        },
        "top_teachers": [
            {
                "teacher_id": teacher_id,
                "name": f"{prenom} {nom}",
                "answers_count": answers_count,
            }
            for teacher_id, nom, prenom, answers_count in top_teachers
        ],
    }


@router.get("/stats/questions")
def get_question_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    total = db.query(StudentQuestion).count()

    by_status = (
        db.query(
            StudentQuestion.status,
            func.count(StudentQuestion.id).label("total")
        )
        .group_by(StudentQuestion.status)
        .order_by(desc("total"))
        .all()
    )

    by_language = (
        db.query(
            StudentQuestion.language,
            func.count(StudentQuestion.id).label("total")
        )
        .group_by(StudentQuestion.language)
        .order_by(desc("total"))
        .all()
    )

    by_subject = (
        db.query(
            Subject.id,
            Subject.name_fr,
            Subject.name_en,
            func.count(StudentQuestion.id).label("total")
        )
        .join(StudentQuestion, StudentQuestion.subject_id == Subject.id)
        .group_by(Subject.id, Subject.name_fr, Subject.name_en)
        .order_by(desc("total"))
        .limit(20)
        .all()
    )

    return {
        "total_questions": total,
        "by_status": [
            {
                "status": status or "UNKNOWN",
                "total": count,
                "percent": percent(count, total),
            }
            for status, count in by_status
        ],
        "by_language": [
            {
                "language": language or "UNKNOWN",
                "total": count,
                "percent": percent(count, total),
            }
            for language, count in by_language
        ],
        "top_subjects": [
            {
                "subject_id": subject_id,
                "name_fr": name_fr,
                "name_en": name_en,
                "questions": count,
                "percent": percent(count, total),
            }
            for subject_id, name_fr, name_en, count in by_subject
        ],
    }


@router.get("/stats/students")
def get_student_admin_stats(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    total_students = db.query(User).filter(User.role == "ELEVE").count()

    active_students = (
        db.query(StudentQuestion.student_id)
        .distinct()
        .count()
    )

    top_students = (
        db.query(
            User.id,
            User.nom,
            User.prenom,
            func.count(StudentQuestion.id).label("questions_count")
        )
        .join(StudentQuestion, StudentQuestion.student_id == User.id)
        .filter(User.role == "ELEVE")
        .group_by(User.id, User.nom, User.prenom)
        .order_by(desc("questions_count"))
        .limit(limit)
        .all()
    )

    return {
        "students": {
            "total": total_students,
            "active": active_students,
            "inactive": max(total_students - active_students, 0),
        },
        "top_students": [
            {
                "student_id": student_id,
                "name": f"{prenom} {nom}",
                "questions_count": questions_count,
            }
            for student_id, nom, prenom, questions_count in top_students
        ],
    }


@router.get("/stats/cache")
def get_cache_admin_stats(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    total_cache_items = db.query(AICache).count()
    total_hits = db.query(func.coalesce(func.sum(AICache.hit_count), 0)).scalar()

    top_cache = (
        db.query(AICache)
        .order_by(AICache.hit_count.desc())
        .limit(limit)
        .all()
    )

    return {
        "cache": {
            "total_items": total_cache_items,
            "total_hits": total_hits,
        },
        "top_cached_questions": [
            {
                "id": item.id,
                "question_text": item.question_text,
                "language": item.language,
                "model_used": item.model_used,
                "hit_count": item.hit_count,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in top_cache
        ],
    }


@router.get("/stats/activity")
def get_activity_admin_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    start_date = date.today() - timedelta(days=days)

    ai_usage_by_day = (
        db.query(
            AIUsageLog.usage_date,
            func.sum(AIUsageLog.request_count).label("requests")
        )
        .filter(AIUsageLog.usage_date >= start_date)
        .group_by(AIUsageLog.usage_date)
        .order_by(AIUsageLog.usage_date.asc())
        .all()
    )

    return {
        "period_days": days,
        "ai_usage_by_day": [
            {
                "date": usage_date,
                "requests": requests,
            }
            for usage_date, requests in ai_usage_by_day
        ],
    }


@router.get("/stats/education")
def get_education_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    total_subjects = db.query(Subject).count()

    subjects_without_teachers = (
        db.query(Subject)
        .outerjoin(TeacherSubject, TeacherSubject.subject_id == Subject.id)
        .filter(TeacherSubject.id.is_(None))
        .count()
    )

    subjects_with_teachers = total_subjects - subjects_without_teachers

    most_difficult_subjects = (
        db.query(
            Subject.id,
            Subject.name_fr,
            Subject.name_en,
            func.count(StudentQuestion.id).label("teacher_requests")
        )
        .join(StudentQuestion, StudentQuestion.subject_id == Subject.id)
        .filter(StudentQuestion.status.in_([
            "REQUESTED_TEACHER",
            "ASSIGNED_TO_TEACHER",
            "ANSWERED_BY_TEACHER",
        ]))
        .group_by(Subject.id, Subject.name_fr, Subject.name_en)
        .order_by(desc("teacher_requests"))
        .limit(20)
        .all()
    )

    return {
        "subjects": {
            "total": total_subjects,
            "with_teachers": subjects_with_teachers,
            "without_teachers": subjects_without_teachers,
            "coverage_rate_percent": percent(subjects_with_teachers, total_subjects),
        },
        "subjects_needing_support": [
            {
                "subject_id": subject_id,
                "name_fr": name_fr,
                "name_en": name_en,
                "teacher_requests": teacher_requests,
            }
            for subject_id, name_fr, name_en, teacher_requests in most_difficult_subjects
        ],
    }


@router.get("/stats/recent")
def get_recent_admin_activity(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    recent_questions = (
        db.query(StudentQuestion)
        .order_by(StudentQuestion.created_at.desc())
        .limit(limit)
        .all()
    )

    recent_ai_answers = (
        db.query(AIAnswer)
        .order_by(AIAnswer.created_at.desc())
        .limit(limit)
        .all()
    )

    recent_teacher_answers = (
        db.query(TeacherAnswer)
        .order_by(TeacherAnswer.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "recent_questions": [
            {
                "id": question.id,
                "student_id": question.student_id,
                "subject_id": question.subject_id,
                "level_id": question.level_id,
                "status": question.status,
                "language": question.language,
                "question_text": question.question_text,
                "created_at": question.created_at,
            }
            for question in recent_questions
        ],
        "recent_ai_answers": [
            {
                "id": answer.id,
                "question_id": answer.question_id,
                "language": answer.language,
                "model_used": answer.model_used,
                "confidence_score": answer.confidence_score,
                "response_type": answer.response_type,
                "created_at": answer.created_at,
            }
            for answer in recent_ai_answers
        ],
        "recent_teacher_answers": [
            {
                "id": answer.id,
                "question_id": answer.question_id,
                "teacher_id": answer.teacher_id,
                "language": answer.language,
                "status": answer.status,
                "created_at": answer.created_at,
            }
            for answer in recent_teacher_answers
        ],
    }


@router.get("/stats/health")
def get_platform_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    waiting_teacher = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.status == "REQUESTED_TEACHER")
        .count()
    )

    assigned_teacher = (
        db.query(StudentQuestion)
        .filter(StudentQuestion.status == "ASSIGNED_TO_TEACHER")
        .count()
    )

    subjects_without_teachers = (
        db.query(Subject)
        .outerjoin(TeacherSubject, TeacherSubject.subject_id == Subject.id)
        .filter(TeacherSubject.id.is_(None))
        .count()
    )

    warnings = []

    if waiting_teacher > 50:
        warnings.append("Beaucoup de questions attendent un enseignant.")

    if assigned_teacher > 100:
        warnings.append("Beaucoup de questions sont prises mais pas encore répondues.")

    if subjects_without_teachers > 0:
        warnings.append("Certaines matières n'ont aucun enseignant assigné.")

    status = "GOOD"

    if warnings:
        status = "WARNING"

    if waiting_teacher > 200 or assigned_teacher > 300:
        status = "CRITICAL"

    return {
        "status": status,
        "warnings": warnings,
        "metrics": {
            "waiting_teacher_questions": waiting_teacher,
            "assigned_teacher_questions": assigned_teacher,
            "subjects_without_teachers": subjects_without_teachers,
        }
    }


@router.patch("/users/{user_id}/role")
def update_admin_user_role(
    user_id: UUID,
    payload: AdminRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    next_role = payload.role.strip().upper()
    if next_role not in GANSEKOU_ROLES:
        raise HTTPException(status_code=400, detail="RÃ´le invalide")

    db_user = db.query(User).filter(User.id == user_id).first()
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
