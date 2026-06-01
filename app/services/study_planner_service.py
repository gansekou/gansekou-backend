from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.models.study_plan import StudyPlan
from app.models.study_plan_item import StudyPlanItem
from app.models.student_skill_progress import StudentSkillProgress
from app.models.content import Content
from app.models.quiz import Quiz


def complete_old_active_plans(db: Session, student_id):
    old_plans = (
        db.query(StudyPlan)
        .filter(
            StudyPlan.student_id == student_id,
            StudyPlan.status == "ACTIVE",
        )
        .all()
    )

    for plan in old_plans:
        plan.status = "ARCHIVED"

    db.commit()


def generate_study_plan(
    db: Session,
    student_id,
    title: str | None = None,
    language: str = "FR",
    duration_days: int = 7,
    max_items: int = 20,
):
    complete_old_active_plans(db, student_id)

    now = datetime.now(timezone.utc)

    plan = StudyPlan(
        student_id=student_id,
        title=title or "Plan de révision personnalisé",
        description="Plan généré automatiquement selon vos faiblesses, vos quiz et votre progression.",
        language=language,
        duration_days=duration_days,
        status="ACTIVE",
        plan_type="PERSONALIZED",
        is_ai_generated=True,
        start_date=now,
        end_date=now + timedelta(days=duration_days),
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    weaknesses = (
        db.query(StudentSkillProgress)
        .filter(
            StudentSkillProgress.student_id == student_id,
            StudentSkillProgress.status.in_(["WEAK", "IN_PROGRESS"]),
        )
        .order_by(StudentSkillProgress.mastery_score.asc())
        .limit(max_items)
        .all()
    )

    items_created = 0
    day_offset = 0

    for weakness in weaknesses:
        if items_created >= max_items:
            break

        content = (
            db.query(Content)
            .filter(
                Content.subject_id == weakness.subject_id,
                Content.level_id == weakness.level_id,
                Content.status.in_(["APPROVED", "PUBLISHED"]),
            )
            .order_by(Content.created_at.desc())
            .first()
        )

        quiz = (
            db.query(Quiz)
            .filter(
                Quiz.subject_id == weakness.subject_id,
                Quiz.level_id == weakness.level_id,
                Quiz.status == "PUBLISHED",
            )
            .order_by(Quiz.created_at.desc())
            .first()
        )

        priority = "HIGH" if weakness.mastery_score < 40 else "NORMAL"

        item = StudyPlanItem(
            study_plan_id=plan.id,
            subject_id=weakness.subject_id,
            level_id=weakness.level_id,
            content_id=content.id if content else None,
            quiz_id=quiz.id if quiz else None,
            title=f"Renforcer : {weakness.skill_name}",
            description=f"Votre maîtrise actuelle est de {weakness.mastery_score}%. Révisez cette compétence puis faites un quiz.",
            item_type="MIXED",
            skill_name=weakness.skill_name,
            priority=priority,
            estimated_minutes=30,
            order_index=items_created,
            scheduled_for=now + timedelta(days=day_offset),
        )

        db.add(item)
        items_created += 1
        day_offset = (day_offset + 1) % duration_days

    if items_created == 0:
        general_item = StudyPlanItem(
            study_plan_id=plan.id,
            title="Faire un quiz de diagnostic",
            description="Aucune faiblesse détectée pour le moment. Commencez par un quiz pour générer un plan personnalisé.",
            item_type="DIAGNOSTIC",
            priority="NORMAL",
            estimated_minutes=20,
            order_index=0,
            scheduled_for=now,
        )

        db.add(general_item)
        items_created = 1

    plan.total_items = items_created

    db.commit()
    db.refresh(plan)

    return plan


def get_active_plan(db: Session, student_id):
    return (
        db.query(StudyPlan)
        .filter(
            StudyPlan.student_id == student_id,
            StudyPlan.status == "ACTIVE",
        )
        .order_by(StudyPlan.created_at.desc())
        .first()
    )


def get_plan_items(db: Session, plan_id):
    return (
        db.query(StudyPlanItem)
        .filter(StudyPlanItem.study_plan_id == plan_id)
        .order_by(StudyPlanItem.order_index.asc())
        .all()
    )


def get_student_plan_history(db: Session, student_id):
    return (
        db.query(StudyPlan)
        .filter(StudyPlan.student_id == student_id)
        .order_by(StudyPlan.created_at.desc())
        .all()
    )


def get_today_items(db: Session, student_id):
    plan = get_active_plan(db, student_id)

    if not plan:
        return []

    now = datetime.now(timezone.utc)
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = start_day + timedelta(days=1)

    return (
        db.query(StudyPlanItem)
        .filter(
            StudyPlanItem.study_plan_id == plan.id,
            StudyPlanItem.scheduled_for >= start_day,
            StudyPlanItem.scheduled_for < end_day,
        )
        .order_by(StudyPlanItem.order_index.asc())
        .all()
    )


def complete_item(db: Session, item_id, student_id):
    item = (
        db.query(StudyPlanItem)
        .join(StudyPlan, StudyPlanItem.study_plan_id == StudyPlan.id)
        .filter(
            StudyPlanItem.id == item_id,
            StudyPlan.student_id == student_id,
        )
        .first()
    )

    if not item:
        return None

    if item.is_completed:
        return item

    item.is_completed = True
    item.completed_at = datetime.now(timezone.utc)

    plan = db.query(StudyPlan).filter(StudyPlan.id == item.study_plan_id).first()

    if plan:
        plan.completed_items += 1

        if plan.completed_items >= plan.total_items:
            plan.status = "COMPLETED"

    db.commit()
    db.refresh(item)

    return item