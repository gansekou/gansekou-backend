from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.content import Content
from app.models.quiz import Quiz
from app.models.teacher_subject import TeacherSubject
from app.models.user import User

ADMIN_ROLES = {"ADMIN", "PROMOTEUR", "ADMINISTRATEUR"}
TEACHER_ROLES = {"ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"}
STUDENT_ROLE = "ELEVE"

OFFICIAL_CONTENT_TYPES = {"COURS", "EXERCICE", "SUJET"}
CONTENT_TYPE_ALIASES = {
    "COURSE": "COURS",
    "COURS": "COURS",
    "PDF": "COURS",
    "VIDEO": "COURS",
    "AUDIO": "COURS",
    "DOCUMENT": "COURS",
    "TOPIC": "COURS",
    "AUTRE": "COURS",
    "EXERCISE": "EXERCICE",
    "EXERCICE": "EXERCICE",
    "EPREUVE": "SUJET",
    "EXAM": "SUJET",
    "SUJET": "SUJET",
}


def normalize_content_type(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return CONTENT_TYPE_ALIASES.get(normalized, "COURS")


def is_admin_role(user: User) -> bool:
    return user.role in ADMIN_ROLES


def get_teacher_subject_ids(db: Session, user: User) -> list:
    return [
        row.subject_id
        for row in db.query(TeacherSubject.subject_id)
        .filter(TeacherSubject.teacher_id == user.id)
        .all()
    ]


def restrict_content_query_by_user(query, current_user: User, db: Session):
    if is_admin_role(current_user):
        return query
    if current_user.role == STUDENT_ROLE:
        if not current_user.level_id:
            return query.filter(False)
        return query.filter(Content.level_id == current_user.level_id)
    if current_user.role in TEACHER_ROLES:
        subject_ids = get_teacher_subject_ids(db, current_user)
        if not subject_ids:
            return query.filter(False)
        return query.filter(Content.subject_id.in_(subject_ids))
    return query.filter(False)


def restrict_quiz_query_by_user(query, current_user: User, db: Session):
    if is_admin_role(current_user):
        return query
    if current_user.role == STUDENT_ROLE:
        if not current_user.level_id:
            return query.filter(False)
        return query.filter(Quiz.level_id == current_user.level_id)
    if current_user.role in TEACHER_ROLES:
        subject_ids = get_teacher_subject_ids(db, current_user)
        if not subject_ids:
            return query.filter(False)
        return query.filter(Quiz.subject_id.in_(subject_ids))
    return query.filter(False)


def require_content_allowed_for_user(db: Session, current_user: User, db_content: Content):
    if is_admin_role(current_user):
        return
    if current_user.role == STUDENT_ROLE:
        if not current_user.level_id:
            raise HTTPException(403, "Choisissez votre niveau pour acceder aux contenus adaptes.")
        if db_content.level_id != current_user.level_id:
            raise HTTPException(403, "Ce contenu ne correspond pas a votre niveau.")
        return
    if current_user.role in TEACHER_ROLES:
        subject_ids = set(get_teacher_subject_ids(db, current_user))
        if db_content.subject_id not in subject_ids:
            raise HTTPException(403, "Cette matiere ne fait pas partie de vos matieres enseignees.")
        return
    raise HTTPException(403, "Acces refuse")


def require_quiz_allowed_for_user(db: Session, current_user: User, quiz: Quiz):
    if is_admin_role(current_user):
        return
    if current_user.role == STUDENT_ROLE:
        if not current_user.level_id:
            raise HTTPException(403, "Choisissez votre niveau pour acceder aux quiz adaptes.")
        if quiz.level_id != current_user.level_id:
            raise HTTPException(403, "Ce quiz ne correspond pas a votre niveau.")
        return
    if current_user.role in TEACHER_ROLES:
        subject_ids = set(get_teacher_subject_ids(db, current_user))
        if quiz.subject_id not in subject_ids:
            raise HTTPException(403, "Cette matiere ne fait pas partie de vos matieres enseignees.")
        return
    raise HTTPException(403, "Acces refuse")
