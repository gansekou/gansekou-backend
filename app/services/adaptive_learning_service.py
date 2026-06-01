from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.quiz import Quiz
from app.models.quiz_question import QuizQuestion
from app.models.quiz_choice import QuizChoice
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_answer import QuizAnswer
from app.models.student_skill_progress import StudentSkillProgress
from app.models.content import Content


def compute_status(mastery_score: int) -> str:
    if mastery_score >= 80:
        return "MASTERED"

    if mastery_score >= 50:
        return "IN_PROGRESS"

    return "WEAK"


def get_or_create_skill_progress(
    db: Session,
    student_id,
    subject_id,
    level_id,
    skill_name: str,
):
    progress = (
        db.query(StudentSkillProgress)
        .filter(
            StudentSkillProgress.student_id == student_id,
            StudentSkillProgress.subject_id == subject_id,
            StudentSkillProgress.level_id == level_id,
            StudentSkillProgress.skill_name == skill_name,
        )
        .first()
    )

    if progress:
        return progress

    progress = StudentSkillProgress(
        student_id=student_id,
        subject_id=subject_id,
        level_id=level_id,
        skill_name=skill_name,
        attempts_count=0,
        correct_count=0,
        wrong_count=0,
        mastery_score=0,
        status="WEAK",
    )

    db.add(progress)
    db.commit()
    db.refresh(progress)

    return progress


def analyze_quiz_attempt(db: Session, attempt_id):
    attempt = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.id == attempt_id)
        .first()
    )

    if not attempt:
        return None

    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()

    if not quiz:
        return None

    answers = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.attempt_id == attempt.id)
        .all()
    )

    for answer in answers:
        question = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.id == answer.question_id)
            .first()
        )

        selected_choice = (
            db.query(QuizChoice)
            .filter(QuizChoice.id == answer.selected_choice_id)
            .first()
        )

        if not question or not selected_choice:
            continue

        skill_name = question.question_type or quiz.quiz_type or "GENERAL"

        progress = get_or_create_skill_progress(
            db=db,
            student_id=attempt.student_id,
            subject_id=quiz.subject_id,
            level_id=quiz.level_id,
            skill_name=skill_name,
        )

        progress.attempts_count += 1

        if selected_choice.is_correct:
            progress.correct_count += 1
        else:
            progress.wrong_count += 1

        progress.mastery_score = int(
            (progress.correct_count / progress.attempts_count) * 100
        )

        progress.status = compute_status(progress.mastery_score)
        progress.last_activity_at = datetime.now(timezone.utc)

    db.commit()

    return True


def get_student_profile(db: Session, student_id):
    progresses = (
        db.query(StudentSkillProgress)
        .filter(StudentSkillProgress.student_id == student_id)
        .all()
    )

    if not progresses:
        return {
            "total_skills": 0,
            "average_mastery": 0,
            "mastered": 0,
            "in_progress": 0,
            "weak": 0,
        }

    total = len(progresses)
    average_mastery = sum(p.mastery_score for p in progresses) / total

    return {
        "total_skills": total,
        "average_mastery": round(average_mastery, 2),
        "mastered": len([p for p in progresses if p.status == "MASTERED"]),
        "in_progress": len([p for p in progresses if p.status == "IN_PROGRESS"]),
        "weak": len([p for p in progresses if p.status == "WEAK"]),
    }


def get_student_weaknesses(db: Session, student_id):
    return (
        db.query(StudentSkillProgress)
        .filter(
            StudentSkillProgress.student_id == student_id,
            StudentSkillProgress.status == "WEAK",
        )
        .order_by(StudentSkillProgress.mastery_score.asc())
        .all()
    )


def get_student_progress(db: Session, student_id):
    return (
        db.query(StudentSkillProgress)
        .filter(StudentSkillProgress.student_id == student_id)
        .order_by(StudentSkillProgress.updated_at.desc())
        .all()
    )


def get_recommendations(db: Session, student_id):
    weaknesses = get_student_weaknesses(db, student_id)

    if not weaknesses:
        return []

    subject_ids = [w.subject_id for w in weaknesses]
    level_ids = [w.level_id for w in weaknesses]

    contents = (
        db.query(Content)
        .filter(
            Content.subject_id.in_(subject_ids),
            Content.level_id.in_(level_ids),
            Content.status.in_(["APPROVED", "PUBLISHED"]),
        )
        .order_by(Content.created_at.desc())
        .limit(20)
        .all()
    )

    return contents