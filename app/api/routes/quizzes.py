import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.core.security import get_current_user
from app.core.content_access import (
    get_teacher_subject_ids,
    require_content_allowed_for_user,
    require_quiz_allowed_for_user,
    restrict_quiz_query_by_user,
)

from app.models.user import User
from app.models.content import Content
from app.models.quiz import Quiz
from app.models.quiz_question import QuizQuestion
from app.models.quiz_choice import QuizChoice
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_answer import QuizAnswer

from app.schemas.quiz import (
    AIQuizGenerateRequest,
    QuizChoiceCreate,
    QuizChoiceResponse,
    QuizChoiceUpdate,
    QuizCreate,
    QuizManageResponse,
    QuizAttemptResponse,
    QuizQuestionCreate,
    QuizQuestionResponse,
    QuizQuestionUpdate,
    QuizResponse,
    QuizResultResponse,
    QuizSubmitPayload,
    QuizUpdate,
)
from app.services.quiz_ai_generator import generate_ai_quiz
from app.services.gamification_service import register_quiz_result
from app.core.premium import require_premium_access, user_has_active_subscription

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]
QUIZ_CREATOR_ROLES = ["ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE", *ADMIN_ROLES]
TEACHER_CREATOR_ROLES = ["ENSEIGNANT", "ENSEIGNANT_EN_ATTENTE"]


def require_teacher_or_admin(user: User):
    if user.role not in QUIZ_CREATOR_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Acces reserve aux enseignants et admins",
        )


def require_student(user: User):
    if user.role != "ELEVE":
        raise HTTPException(status_code=403, detail="Acces reserve aux eleves")


def is_admin(user: User) -> bool:
    return user.role in ADMIN_ROLES


def can_access_premium(db: Session, user: User) -> bool:
    return user.role != "ELEVE" or user_has_active_subscription(db, user.id)


def restrict_premium_quiz_query(query, db: Session, user: User):
    if can_access_premium(db, user):
        return query
    return query.filter(Quiz.is_premium == False)


def require_quiz_access(db: Session, user: User, quiz: Quiz):
    require_quiz_allowed_for_user(db, user, quiz)
    if quiz.status != "PUBLISHED" and not is_admin(user) and quiz.author_id != user.id:
        raise HTTPException(403, "Quiz non disponible")

    if quiz.is_premium and user.role == "ELEVE":
        require_premium_access(db, user.id)


def require_quiz_management(user: User, quiz: Quiz):
    require_teacher_or_admin(user)
    if user.role in TEACHER_CREATOR_ROLES and quiz.author_id != user.id:
        raise HTTPException(403, "Vous ne pouvez modifier que vos propres quiz")


def apply_course_to_quiz_payload(db: Session, user: User, payload):
    if not payload.course_id:
        if user.role in TEACHER_CREATOR_ROLES:
            subject_ids = set(get_teacher_subject_ids(db, user))
            if payload.subject_id not in subject_ids:
                raise HTTPException(403, "Cette matiere ne fait pas partie de vos matieres enseignees.")
        return payload.subject_id, payload.level_id, None

    course = db.query(Content).filter(Content.id == payload.course_id).first()
    if not course:
        raise HTTPException(404, "Cours lie introuvable")
    if course.content_type != "COURS":
        raise HTTPException(400, "Le quiz doit etre lie a un contenu de type COURS")
    require_content_allowed_for_user(db, user, course)
    return course.subject_id, course.level_id, course.id


def quiz_with_questions_query(db: Session):
    return db.query(Quiz).options(
        selectinload(Quiz.questions).selectinload(QuizQuestion.choices),
        selectinload(Quiz.author),
        selectinload(Quiz.subject),
        selectinload(Quiz.level),
        selectinload(Quiz.course),
    )


def get_quiz_or_404(db: Session, quiz_id: uuid.UUID) -> Quiz:
    quiz = quiz_with_questions_query(db).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(404, "Quiz introuvable")
    return quiz


def get_question_or_404(db: Session, question_id: uuid.UUID) -> QuizQuestion:
    question = (
        db.query(QuizQuestion)
        .options(selectinload(QuizQuestion.quiz), selectinload(QuizQuestion.choices))
        .filter(QuizQuestion.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(404, "Question introuvable")
    return question


def get_choice_or_404(db: Session, choice_id: uuid.UUID) -> QuizChoice:
    choice = (
        db.query(QuizChoice)
        .options(
            selectinload(QuizChoice.question).selectinload(QuizQuestion.quiz),
        )
        .filter(QuizChoice.id == choice_id)
        .first()
    )
    if not choice:
        raise HTTPException(404, "Choix introuvable")
    return choice


def normalize_selected_ids(value: str | list[str] | None) -> set[uuid.UUID]:
    if not value:
        return set()
    raw_values = value if isinstance(value, list) else [value]
    selected_ids = set()
    for raw in raw_values:
        try:
            selected_ids.add(uuid.UUID(str(raw)))
        except ValueError:
            continue
    return selected_ids


def build_attempt_result(db: Session, attempt: QuizAttempt) -> dict:
    quiz = get_quiz_or_404(db, attempt.quiz_id)
    answers = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.attempt_id == attempt.id)
        .all()
    )
    selected_by_question: dict[uuid.UUID, set[uuid.UUID]] = {}
    for answer in answers:
        selected_by_question.setdefault(answer.question_id, set()).add(
            answer.selected_choice_id
        )

    results = []
    total_points = 0
    earned_points = 0
    correct_answers = 0

    for question in quiz.questions:
        total_points += question.points
        correct_choice_ids = {
            choice.id for choice in question.choices if choice.is_correct
        }
        selected_choice_ids = selected_by_question.get(question.id, set())
        is_correct = bool(correct_choice_ids) and selected_choice_ids == correct_choice_ids
        earned = question.points if is_correct else 0
        earned_points += earned
        if is_correct:
            correct_answers += 1

        results.append({
            "question_id": question.id,
            "selected_choice_ids": list(selected_choice_ids),
            "correct_choice_ids": list(correct_choice_ids),
            "is_correct": is_correct,
            "points": question.points,
            "earned_points": earned,
            "explanation": question.explanation,
        })

    score = int((earned_points / total_points) * 100) if total_points > 0 else 0

    return {
        "quiz_id": quiz.id,
        "attempt_id": attempt.id,
        "score": score,
        "passed": score >= quiz.passing_score,
        "correct_answers": correct_answers,
        "total_questions": len(quiz.questions),
        "results": results,
    }


@router.post("/", response_model=QuizResponse)
def create_quiz(
    payload: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_teacher_or_admin(current_user)

    subject_id, level_id, course_id = apply_course_to_quiz_payload(db, current_user, payload)

    quiz = Quiz(
        author_id=current_user.id,
        title=payload.title,
        description=payload.description,
        course_id=course_id,
        content_id=course_id,
        subject_id=subject_id,
        level_id=level_id,
        language=payload.language,
        difficulty_level=payload.difficulty_level,
        quiz_type=payload.quiz_type,
        is_premium=payload.is_premium,
        is_randomized=payload.is_randomized,
        allow_retry=payload.allow_retry,
        passing_score=payload.passing_score,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        status="PUBLISHED",
    )

    db.add(quiz)
    db.commit()
    return get_quiz_or_404(db, quiz.id)


@router.get("/", response_model=list[QuizResponse])
def get_quizzes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = quiz_with_questions_query(db).filter(Quiz.status == "PUBLISHED")
    query = restrict_quiz_query_by_user(query, current_user, db)
    return restrict_premium_quiz_query(query, db, current_user).offset(skip).limit(limit).all()


@router.get("/me/history", response_model=list[QuizAttemptResponse])
def get_my_quiz_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == current_user.id)
        .order_by(QuizAttempt.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/attempts/{attempt_id}", response_model=QuizResultResponse)
def get_attempt_result(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(404, "Tentative introuvable")

    quiz = get_quiz_or_404(db, attempt.quiz_id)
    if current_user.role == "ELEVE" and attempt.student_id != current_user.id:
        raise HTTPException(403, "Resultat non disponible")
    if current_user.role in TEACHER_CREATOR_ROLES and quiz.author_id != current_user.id:
        raise HTTPException(403, "Resultat non disponible")
    if current_user.role not in ["ELEVE", *TEACHER_CREATOR_ROLES, *ADMIN_ROLES]:
        raise HTTPException(403, "Resultat non disponible")

    require_quiz_access(db, current_user, quiz)
    return build_attempt_result(db, attempt)


@router.post("/ai/generate")
def generate_quiz_with_ai(
    payload: AIQuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_teacher_or_admin(current_user)
    subject_id, level_id, course_id = apply_course_to_quiz_payload(db, current_user, payload)
    generated = generate_ai_quiz(payload)

    quiz = Quiz(
        author_id=current_user.id,
        course_id=course_id,
        content_id=course_id,
        subject_id=subject_id,
        level_id=level_id,
        title=generated["title"],
        description=generated["description"],
        language=payload.language,
        difficulty_level=payload.difficulty_level,
        quiz_type="QCM",
        status="PUBLISHED",
        total_questions=len(generated["questions"]),
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    for index, generated_question in enumerate(generated["questions"]):
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=generated_question["question_text"],
            explanation=generated_question["explanation"],
            points=generated_question["points"],
            order_index=index,
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        for generated_choice in generated_question["choices"]:
            db.add(QuizChoice(
                question_id=question.id,
                choice_text=generated_choice["choice_text"],
                is_correct=generated_choice["is_correct"],
            ))

    db.commit()

    return {
        "message": "Quiz IA genere avec succes",
        "quiz_id": quiz.id,
        "total_questions": quiz.total_questions,
    }


@router.get("/by-course/{course_id}", response_model=list[QuizResponse])
def get_quizzes_by_course(
    course_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = db.query(Content).filter(Content.id == course_id).first()
    if not course:
        raise HTTPException(404, "Cours introuvable")
    if course.content_type != "COURS":
        raise HTTPException(400, "Le contenu demande n'est pas un cours")
    require_content_allowed_for_user(db, current_user, course)

    query = (
        quiz_with_questions_query(db)
        .filter(
            Quiz.status == "PUBLISHED",
            Quiz.course_id == course_id,
        )
    )
    query = restrict_quiz_query_by_user(query, current_user, db)
    return restrict_premium_quiz_query(query, db, current_user).offset(skip).limit(limit).all()


@router.post("/questions/{question_id}/choices", response_model=QuizChoiceResponse)
def add_choice_to_question(
    question_id: uuid.UUID,
    payload: QuizChoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_question_or_404(db, question_id)
    require_quiz_management(current_user, question.quiz)

    choice = QuizChoice(
        question_id=question.id,
        choice_text=payload.choice_text,
        is_correct=payload.is_correct,
    )
    db.add(choice)
    db.commit()
    db.refresh(choice)
    return choice


@router.put("/questions/{question_id}", response_model=QuizQuestionResponse)
def update_question(
    question_id: uuid.UUID,
    payload: QuizQuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_question_or_404(db, question_id)
    require_quiz_management(current_user, question.quiz)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)
    return get_question_or_404(db, question.id)


@router.delete("/questions/{question_id}", response_model=QuizQuestionResponse)
def delete_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_question_or_404(db, question_id)
    require_quiz_management(current_user, question.quiz)
    response = question
    question.quiz.total_questions = max(0, question.quiz.total_questions - 1)
    db.delete(question)
    db.commit()
    return response


@router.put("/choices/{choice_id}", response_model=QuizChoiceResponse)
def update_choice(
    choice_id: uuid.UUID,
    payload: QuizChoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    choice = get_choice_or_404(db, choice_id)
    require_quiz_management(current_user, choice.question.quiz)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(choice, field, value)

    db.commit()
    db.refresh(choice)
    return choice


@router.delete("/choices/{choice_id}", response_model=QuizChoiceResponse)
def delete_choice(
    choice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    choice = get_choice_or_404(db, choice_id)
    require_quiz_management(current_user, choice.question.quiz)
    response = choice
    db.delete(choice)
    db.commit()
    return response


@router.get("/{quiz_id}", response_model=QuizResponse)
def get_quiz(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = get_quiz_or_404(db, quiz_id)
    require_quiz_access(db, current_user, quiz)
    return quiz


@router.get("/{quiz_id}/manage", response_model=QuizManageResponse)
def get_quiz_for_management(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = get_quiz_or_404(db, quiz_id)
    require_quiz_management(current_user, quiz)
    return quiz


@router.put("/{quiz_id}", response_model=QuizManageResponse)
def update_quiz(
    quiz_id: uuid.UUID,
    payload: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = get_quiz_or_404(db, quiz_id)
    require_quiz_management(current_user, quiz)

    values = payload.model_dump(exclude_unset=True)
    if "status" in values and not is_admin(current_user):
        raise HTTPException(403, "Seule l'administration peut changer le statut")
    if "course_id" in values:
        if values["course_id"] is None:
            quiz.course_id = None
            quiz.content_id = None
            values.pop("course_id")
        else:
            course = db.query(Content).filter(Content.id == values["course_id"]).first()
            if not course:
                raise HTTPException(404, "Cours lie introuvable")
            if course.content_type != "COURS":
                raise HTTPException(400, "Le quiz doit etre lie a un contenu de type COURS")
            require_content_allowed_for_user(db, current_user, course)
            values["course_id"] = course.id
            values["content_id"] = course.id
            values["subject_id"] = course.subject_id
            values["level_id"] = course.level_id

    for field, value in values.items():
        setattr(quiz, field, value)

    db.commit()
    return get_quiz_or_404(db, quiz.id)


@router.delete("/{quiz_id}", response_model=QuizManageResponse)
def delete_quiz(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = get_quiz_or_404(db, quiz_id)
    require_quiz_management(current_user, quiz)
    response = quiz
    db.delete(quiz)
    db.commit()
    return response


@router.post("/{quiz_id}/questions", response_model=QuizQuestionResponse)
def add_question_to_quiz(
    quiz_id: uuid.UUID,
    payload: QuizQuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = get_quiz_or_404(db, quiz_id)
    require_quiz_management(current_user, quiz)

    order_index = payload.order_index
    if order_index == 0 and quiz.questions:
        order_index = max(question.order_index for question in quiz.questions) + 1

    question = QuizQuestion(
        quiz_id=quiz.id,
        question_text=payload.question_text,
        question_image_url=payload.question_image_url,
        explanation=payload.explanation,
        question_type=payload.question_type,
        points=payload.points,
        order_index=order_index,
        is_required=payload.is_required,
    )

    db.add(question)
    quiz.total_questions += 1
    db.commit()
    return get_question_or_404(db, question.id)


@router.post("/{quiz_id}/start")
def start_quiz(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)
    quiz = get_quiz_or_404(db, quiz_id)

    if quiz.status != "PUBLISHED":
        raise HTTPException(403, "Quiz non disponible")

    require_quiz_access(db, current_user, quiz)

    if not quiz.questions:
        raise HTTPException(400, "Ce quiz ne contient aucune question")

    if not quiz.allow_retry:
        existing_attempt = (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz.id,
                QuizAttempt.student_id == current_user.id,
            )
            .first()
        )
        if existing_attempt:
            raise HTTPException(400, "Vous avez deja passe ce quiz")

    active_attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.student_id == current_user.id,
            QuizAttempt.completed_at == None,
        )
        .order_by(QuizAttempt.started_at.desc())
        .first()
    )
    if active_attempt:
        return {
            "attempt_id": active_attempt.id,
            "quiz_id": quiz.id,
            "started_at": active_attempt.started_at,
            "resumed": True,
        }

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=current_user.id,
        total_questions=len(quiz.questions),
    )
    quiz.total_attempts += 1

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": attempt.id,
        "quiz_id": quiz.id,
        "started_at": attempt.started_at,
        "resumed": False,
    }


@router.post("/{quiz_id}/submit/{attempt_id}", response_model=QuizResultResponse)
def submit_quiz(
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    payload: QuizSubmitPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_student(current_user)

    attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.id == attempt_id,
            QuizAttempt.student_id == current_user.id,
        )
        .first()
    )
    if not attempt:
        raise HTTPException(404, "Tentative introuvable")

    quiz = get_quiz_or_404(db, quiz_id)
    if quiz.status != "PUBLISHED":
        raise HTTPException(403, "Quiz non disponible")
    require_quiz_access(db, current_user, quiz)

    if attempt.quiz_id != quiz.id:
        raise HTTPException(400, "Cette tentative ne correspond pas a ce quiz")
    if attempt.completed_at is not None:
        raise HTTPException(400, "Ce quiz a deja ete soumis")

    total_points = 0
    earned_points = 0
    correct_answers = 0

    for question in quiz.questions:
        total_points += question.points
        selected_choice_ids = normalize_selected_ids(
            payload.answers.get(str(question.id))
        )
        valid_choice_ids = {choice.id for choice in question.choices}
        correct_choice_ids = {
            choice.id for choice in question.choices if choice.is_correct
        }
        selected_choice_ids = selected_choice_ids.intersection(valid_choice_ids)

        for selected_choice_id in selected_choice_ids:
            db.add(QuizAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_choice_id=selected_choice_id,
            ))

        is_correct = bool(correct_choice_ids) and selected_choice_ids == correct_choice_ids
        if is_correct:
            earned_points += question.points
            correct_answers += 1

    score = int((earned_points / total_points) * 100) if total_points > 0 else 0

    attempt.score = score
    attempt.correct_answers = correct_answers
    attempt.total_questions = len(quiz.questions)
    attempt.is_passed = score >= quiz.passing_score
    attempt.completed_at = datetime.now(timezone.utc)

    register_quiz_result(
        db=db,
        student_id=current_user.id,
        passed=attempt.is_passed,
        score=score,
    )

    db.commit()
    db.refresh(attempt)
    return build_attempt_result(db, attempt)


@router.get("/{quiz_id}/leaderboard", response_model=list[QuizAttemptResponse])
def get_quiz_leaderboard(
    quiz_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = get_quiz_or_404(db, quiz_id)
    require_quiz_access(db, current_user, quiz)
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.completed_at != None)
        .order_by(QuizAttempt.score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{quiz_id}/analytics")
def get_quiz_analytics(
    quiz_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = get_quiz_or_404(db, quiz_id)
    require_quiz_access(db, current_user, quiz)

    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz.id, QuizAttempt.completed_at != None)
        .all()
    )

    total_attempts = len(attempts)
    average_score = (
        sum(attempt.score for attempt in attempts) / total_attempts
        if total_attempts > 0 else 0
    )
    passed_count = len([attempt for attempt in attempts if attempt.is_passed])

    return {
        "quiz_id": quiz.id,
        "total_attempts": total_attempts,
        "average_score": round(average_score, 2),
        "pass_rate": (
            round((passed_count / total_attempts) * 100, 2)
            if total_attempts > 0 else 0
        ),
    }
