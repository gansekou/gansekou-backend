import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.websocket_manager import websocket_manager
from app.models.badge import Badge
from app.models.student_badge import StudentBadge
from app.models.student_gamification import StudentGamification

DEFAULT_BADGES = [
    ("FIRST_QUIZ", "Premier Quiz", "First Quiz", 0, 1),
    ("STREAK_7", "Série de 7 jours", "7-day streak", 150, 0),
    ("STREAK_30", "Série de 30 jours", "30-day streak", 700, 0),
    ("MATH_EXPERT", "Expert Mathématiques", "Mathematics Expert", 600, 10),
    ("FRENCH_EXPERT", "Expert Français", "French Expert", 600, 10),
    ("EXPLORER", "Explorateur", "Explorer", 100, 0),
    ("QUIZ_MASTER", "Quiz Master", "Quiz Master", 900, 25),
    ("PREMIUM_LEARNER", "Apprenant Premium", "Premium Learner", 250, 3),
    ("GANSEKOU_ELITE", "Elite Gansekou", "Gansekou Elite", 1500, 40),
    ("CALC_GENIUS", "Génie du calcul", "Calculation Genius", 800, 20),
    ("INTENSIVE_READER", "Lecture intensive", "Intensive Reader", 400, 0),
    ("PERSEVERANT", "Persévérant", "Persistent", 500, 8),
    ("AI_CHAMPION", "Champion IA", "AI Champion", 350, 0),
    ("CURIOUS", "Curieux", "Curious", 120, 0),
    ("TOP_10", "Top 10 classement", "Top 10 leaderboard", 1200, 20),
    ("TEACHER_FIRST_CONTENT", "Premier contenu publié", "First published content", 100, 0),
    ("TEACHER_10_ANSWERS", "10 réponses enseignants", "10 teacher answers", 200, 0),
    ("TEACHER_100_ANSWERS", "100 réponses enseignants", "100 teacher answers", 2000, 0),
    ("TEACHER_POPULAR", "Enseignant populaire", "Popular Teacher", 500, 0),
    ("PEDAGOGY_EXPERT", "Expert pédagogie", "Pedagogy Expert", 900, 0),
    ("ELITE_MENTOR", "Mentor Elite", "Elite Mentor", 1500, 0),
    ("ACTIVE_CREATOR", "Créateur actif", "Active Creator", 700, 0),
    ("MATH_MASTER_TEACHER", "Maître des mathématiques", "Mathematics Master Teacher", 1200, 0),
    ("VERIFIED_TEACHER", "Professeur vérifié", "Verified Teacher", 50, 0),
    ("HIGH_IMPACT_TEACHER", "Impact pédagogique élevé", "High Teaching Impact", 1800, 0),
    ("PREMIUM_TEACHER", "Enseignant Premium", "Premium Teacher", 300, 0),
    ("TOP_TEACHER_MONTH", "Top enseignant du mois", "Top Teacher of the Month", 2200, 0),
]


def calculate_level(points: int) -> int:
    return max(1, points // 100 + 1)


def level_label(points: int, role: str = "ELEVE") -> str:
    teacher_levels = [
        "Assistant",
        "Formateur",
        "Mentor",
        "Expert",
        "Professeur Elite",
        "Maître pédagogique",
    ]
    learner_levels = [
        "Débutant",
        "Explorateur",
        "Apprenant",
        "Expert",
        "Elite",
        "Maître",
        "Légende",
    ]
    labels = teacher_levels if role == "ENSEIGNANT" else learner_levels
    index = min(len(labels) - 1, max(0, points // 500))
    return labels[index]


def ensure_default_badges(db: Session):
    existing_codes = {
        code for (code,) in db.query(Badge.code).all()
    }

    created = []
    for code, name_fr, name_en, required_points, required_quizzes in DEFAULT_BADGES:
        if code in existing_codes:
            continue

        badge = Badge(
            code=code,
            name_fr=name_fr,
            name_en=name_en,
            description_fr=f"Badge Gansekou débloqué avec {required_points} XP.",
            description_en=f"Gansekou badge unlocked with {required_points} XP.",
            required_points=required_points,
            required_quizzes_completed=required_quizzes,
            is_active=True,
        )
        db.add(badge)
        created.append(badge)

    if created:
        db.commit()

    return created


def get_or_create_profile(db: Session, student_id):
    profile = (
        db.query(StudentGamification)
        .filter(StudentGamification.student_id == student_id)
        .first()
    )

    if profile:
        return profile

    profile = StudentGamification(student_id=student_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile


def award_points(db: Session, student_id, points: int):
    profile = get_or_create_profile(db, student_id)

    profile.points += points
    profile.level = calculate_level(profile.points)
    profile.last_activity_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)

    check_and_award_badges(db, student_id)
    send_live_gamification_event(student_id, points, profile.points)

    return profile


def register_quiz_result(db: Session, student_id, passed: bool, score: int):
    profile = get_or_create_profile(db, student_id)

    gained_points = max(5, score // 2)

    profile.points += gained_points
    profile.level = calculate_level(profile.points)
    profile.quizzes_completed += 1

    if passed:
        profile.quizzes_passed += 1

    profile.last_activity_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)

    check_and_award_badges(db, student_id)
    send_live_gamification_event(student_id, gained_points, profile.points)

    return profile


def send_live_gamification_event(user_id, gained_points: int, total_points: int):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    loop.create_task(
        websocket_manager.send_to_user(
            user_id,
            {
                "type": "XP_GAINED",
                "title": "XP Gansekou",
                "message": f"+{gained_points} XP",
                "xp": gained_points,
                "total_xp": total_points,
            },
        )
    )


def check_and_award_badges(db: Session, student_id):
    ensure_default_badges(db)
    profile = get_or_create_profile(db, student_id)

    badges = (
        db.query(Badge)
        .filter(Badge.is_active == True)
        .all()
    )

    awarded = []

    for badge in badges:
        already = (
            db.query(StudentBadge)
            .filter(
                StudentBadge.student_id == student_id,
                StudentBadge.badge_id == badge.id,
            )
            .first()
        )

        if already:
            continue

        eligible = (
            profile.points >= badge.required_points
            and profile.quizzes_completed >= badge.required_quizzes_completed
        )

        if eligible:
            student_badge = StudentBadge(
                student_id=student_id,
                badge_id=badge.id,
            )

            db.add(student_badge)
            awarded.append(badge)
            send_live_badge_event(student_id, badge.name_fr)

    db.commit()

    return awarded


def send_live_badge_event(user_id, badge_name: str):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    loop.create_task(
        websocket_manager.send_to_user(
            user_id,
            {
                "type": "BADGE_UNLOCKED",
                "title": "Badge débloqué",
                "message": badge_name,
            },
        )
    )
