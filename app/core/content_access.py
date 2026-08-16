from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.content import Content
from app.models.content_level import ContentLevel
from app.models.quiz import Quiz
from app.models.teacher_subject import TeacherSubject
from app.models.user import User


ADMIN_ROLES = {
    "ADMIN",
    "PROMOTEUR",
    "ADMINISTRATEUR",
}

TEACHER_ROLES = {
    "ENSEIGNANT",
    "ENSEIGNANT_EN_ATTENTE",
}

STUDENT_ROLE = "ELEVE"


OFFICIAL_CONTENT_TYPES = {
    "COURS",
    "EXERCICE",
    "SUJET",
}


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


def normalize_content_type(
    value: str | None,
) -> str:
    normalized = (value or "").strip().upper()

    return CONTENT_TYPE_ALIASES.get(
        normalized,
        normalized,
    )


def is_admin_role(
    user: User,
) -> bool:
    return user.role in ADMIN_ROLES


def get_teacher_subject_ids(
    db: Session,
    user: User,
) -> list:
    return [
        row.subject_id
        for row in (
            db.query(TeacherSubject.subject_id)
            .filter(
                TeacherSubject.teacher_id == user.id
            )
            .all()
        )
    ]


# ============================================================
# CONTENTS
# ============================================================

def restrict_content_query_by_user(
    query,
    current_user: User,
    db: Session,
):
    """
    Restreint les contenus accessibles selon le rôle.

    ELEVE:
        Le contenu doit être associé au niveau de l'élève
        via la table content_levels.

    ENSEIGNANT:
        Le contenu doit appartenir à une matière enseignée
        par l'enseignant.

    ADMIN:
        Accès complet.
    """

    # --------------------------------------------------------
    # ADMIN / PROMOTEUR / ADMINISTRATEUR
    # --------------------------------------------------------

    if is_admin_role(current_user):
        return query

    # --------------------------------------------------------
    # ELEVE
    # --------------------------------------------------------

    if current_user.role == STUDENT_ROLE:

        if not current_user.level_id:
            return query.filter(False)

        return (
            query
            .join(
                ContentLevel,
                ContentLevel.content_id == Content.id,
            )
            .filter(
                ContentLevel.level_id
                == current_user.level_id
            )
            .distinct()
        )

    # --------------------------------------------------------
    # ENSEIGNANT
    # --------------------------------------------------------

    if current_user.role in TEACHER_ROLES:

        subject_ids = get_teacher_subject_ids(
            db,
            current_user,
        )

        if not subject_ids:
            return query.filter(False)

        return query.filter(
            Content.subject_id.in_(subject_ids)
        )

    # --------------------------------------------------------
    # AUTRES ROLES
    # --------------------------------------------------------

    return query.filter(False)


# ============================================================
# QUIZ
# ============================================================

def restrict_quiz_query_by_user(
    query,
    current_user: User,
    db: Session,
):
    if is_admin_role(current_user):
        return query

    if current_user.role == STUDENT_ROLE:

        if not current_user.level_id:
            return query.filter(False)

        return query.filter(
            Quiz.level_id
            == current_user.level_id
        )

    if current_user.role in TEACHER_ROLES:

        subject_ids = get_teacher_subject_ids(
            db,
            current_user,
        )

        if not subject_ids:
            return query.filter(False)

        return query.filter(
            Quiz.subject_id.in_(subject_ids)
        )

    return query.filter(False)


# ============================================================
# AUTORISATION D'UN CONTENT INDIVIDUEL
# ============================================================

def require_content_allowed_for_user(
    db: Session,
    current_user: User,
    db_content: Content,
):
    """
    Vérifie qu'un utilisateur a le droit d'accéder
    à un contenu précis.
    """

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if is_admin_role(current_user):
        return

    # --------------------------------------------------------
    # ELEVE
    # --------------------------------------------------------

    if current_user.role == STUDENT_ROLE:

        if not current_user.level_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Choisissez votre niveau pour "
                    "acceder aux contenus adaptes."
                ),
            )

        # IMPORTANT :
        # Le contenu peut maintenant avoir plusieurs niveaux.
        #
        # db_content.levels contient tous les niveaux
        # associés au contenu.

        allowed = any(
            level.id == current_user.level_id
            for level in db_content.levels
        )

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Ce contenu ne correspond pas "
                    "a votre niveau."
                ),
            )

        return

    # --------------------------------------------------------
    # ENSEIGNANT
    # --------------------------------------------------------

    if current_user.role in TEACHER_ROLES:

        subject_ids = set(
            get_teacher_subject_ids(
                db,
                current_user,
            )
        )

        if db_content.subject_id not in subject_ids:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Cette matiere ne fait pas partie "
                    "de vos matieres enseignees."
                ),
            )

        return

    # --------------------------------------------------------
    # AUTRES
    # --------------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail="Acces refuse",
    )


# ============================================================
# AUTORISATION QUIZ
# ============================================================

def require_quiz_allowed_for_user(
    db: Session,
    current_user: User,
    quiz: Quiz,
):
    if is_admin_role(current_user):
        return

    if current_user.role == STUDENT_ROLE:

        if not current_user.level_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Choisissez votre niveau pour "
                    "acceder aux quiz adaptes."
                ),
            )

        if quiz.level_id != current_user.level_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Ce quiz ne correspond pas "
                    "a votre niveau."
                ),
            )

        return

    if current_user.role in TEACHER_ROLES:

        subject_ids = set(
            get_teacher_subject_ids(
                db,
                current_user,
            )
        )

        if quiz.subject_id not in subject_ids:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Cette matiere ne fait pas partie "
                    "de vos matieres enseignees."
                ),
            )

        return

    raise HTTPException(
        status_code=403,
        detail="Acces refuse",
    )
