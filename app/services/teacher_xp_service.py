from sqlalchemy.orm import Session

from app.models.user import User
from app.services.gamification_service import award_points

XP_ANSWER_QUESTION = 20
XP_CONTENT_VIEW = 2
XP_CONTENT_DOWNLOAD = 5
XP_QUIZ_COMPLETED = 10


def award_teacher_xp(db: Session, teacher_id, points: int):
    teacher = db.query(User).filter(User.id == teacher_id).first()

    if not teacher or teacher.role != "ENSEIGNANT":
        return None

    return award_points(db, teacher_id, points)
