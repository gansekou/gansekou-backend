import uuid
import hashlib
import re
import unicodedata
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user
from app.services.ai_service import ask_ai
from app.core.config import settings

from app.models.ai_cache import AICache
from app.models.ai_usage_log import AIUsageLog
from app.models.student_question import StudentQuestion
from app.models.ai_answer import AIAnswer
from app.models.notification import Notification
from app.models.level import Level
from app.models.subject import Subject

from app.crud.teacher_subject import teacher_subject

from fastapi import BackgroundTasks
from app.core.websocket_manager import websocket_manager

from app.core.premium import require_premium_access

router = APIRouter()

DAILY_AI_LIMIT_ELEVE = 20
DAILY_AI_LIMIT_ENSEIGNANT = 50
DAILY_AI_LIMIT_ADMIN = 200


class AIChatRequest(BaseModel):
    question: str
    subject_id: uuid.UUID | None = None
    level_id: uuid.UUID | None = None
    language: str = "FR"
    mode: str = "STUDENT_HELP"


class AIChatResponse(BaseModel):
    answer: str
    cached: bool
    remaining_requests: int


class AIGenerationRequest(BaseModel):
    topic: str
    subject_id: uuid.UUID | None = None
    level_id: uuid.UUID | None = None
    language: str = "FR"
    difficulty: str = "INTERMEDIATE"
    count: int = 5


def normalize_question(question: str) -> str:
    question = question.lower().strip()

    question = unicodedata.normalize("NFD", question)
    question = "".join(
        c for c in question
        if unicodedata.category(c) != "Mn"
    )

    question = re.sub(r"http\S+", " ", question)
    question = re.sub(r"\S+@\S+", " ", question)
    question = re.sub(r"[^\w\s]", " ", question)
    question = re.sub(r"\s+", " ", question).strip()

    typo_fixes = {
        "histoir": "histoire",
        "equationn": "equation",
        "eqution": "equation",
        "mat": "mathematique",
        "maths": "mathematique",
        "svt": "science vie terre",
        "pc": "physique chimie",
        "geo": "geographie",
    }

    words = question.split()
    corrected_words = [typo_fixes.get(word, word) for word in words]
    question = " ".join(corrected_words)

    intent_patterns = {
        r"\b(definition|defini|definir|explique|cest quoi|quest ce que|what is|define)\b": "definition",
        r"\b(resous|resoudre|solution|solve|calcul)\b": "resolution",
        r"\b(pourquoi|why|raison|cause)\b": "explication",
        r"\b(compare|difference|diff|versus|vs)\b": "comparaison",
        r"\b(exemple|example|illustration)\b": "exemple",
    }

    detected_intents = []

    for pattern, intent in intent_patterns.items():
        if re.search(pattern, question):
            detected_intents.append(intent)

    stop_words = {
        "le", "la", "les", "un", "une", "des", "du", "de", "d",
        "et", "en", "au", "aux", "pour", "avec", "sur", "dans",
        "the", "a", "an", "of", "to", "is", "are", "please", "stp",
    }

    filtered_words = [
        word for word in question.split()
        if word not in stop_words
    ]

    question = " ".join(filtered_words)

    stemming_rules = {
        "mathematiques": "mathematique",
        "equations": "equation",
        "histoires": "histoire",
        "definitions": "definition",
        "fonctions": "fonction",
        "exercices": "exercice",
    }

    final_words = [
        stemming_rules.get(word, word)
        for word in question.split()
    ]

    question = " ".join(final_words)

    unique_words = sorted(set(question.split()))
    normalized = " ".join(unique_words)

    if detected_intents:
        normalized += " " + " ".join(sorted(set(detected_intents)))

    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def make_question_hash(question: str, language: str) -> str:
    normalized = normalize_question(question)
    raw = f"{language}:{normalized}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_daily_limit(role: str) -> int:
    if role == "ELEVE":
        return DAILY_AI_LIMIT_ELEVE

    if role == "ENSEIGNANT":
        return DAILY_AI_LIMIT_ENSEIGNANT

    return DAILY_AI_LIMIT_ADMIN


def get_or_create_usage(db: Session, user_id, model_used: str):
    today = date.today()

    usage = (
        db.query(AIUsageLog)
        .filter(AIUsageLog.user_id == user_id)
        .filter(AIUsageLog.usage_date == today)
        .first()
    )

    if usage:
        return usage

    usage = AIUsageLog(
        user_id=user_id,
        usage_date=today,
        request_count=0,
        model_used=model_used,
    )

    db.add(usage)
    db.commit()
    db.refresh(usage)

    return usage


@router.post("/chat", response_model=AIChatResponse)
def ai_chat(
    payload: AIChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    question = payload.question.strip()

    if current_user.role == "ELEVE":
        require_premium_access(db, current_user.id)

    if len(question) < 3:
        raise HTTPException(
            status_code=400,
            detail="Question trop courte",
        )

    daily_limit = get_daily_limit(current_user.role)
    usage = get_or_create_usage(
        db=db,
        user_id=current_user.id,
        model_used=settings.OPENAI_MODEL,
    )

    if usage.request_count >= daily_limit:
        db_question = StudentQuestion(
            student_id=current_user.id,
            subject_id=payload.subject_id,
            level_id=payload.level_id,
            question_text=question,
            language=payload.language,
            status="REQUESTED_TEACHER",
            teacher_requested=True,
            sync_status="SYNCED",
        )

        db.add(db_question)

        student_notification = Notification(
            user_id=current_user.id,
            title="Quota IA atteint",
            message="Votre quota IA est atteint. Votre question a été transmise à un enseignant.",
            language=payload.language,
            type="QUESTION_SENT_TO_TEACHER",
        )

        db.add(student_notification)
        db.commit()

        return {
            "answer": "Votre quota IA journalier est atteint. Votre question a été transmise à un enseignant.",
            "cached": False,
            "remaining_requests": 0,
        }

    question_hash = make_question_hash(question, payload.language)

    cached_answer = (
        db.query(AICache)
        .filter(AICache.question_hash == question_hash)
        .first()
    )

    db_question = StudentQuestion(
        student_id=current_user.id,
        subject_id=payload.subject_id,
        level_id=payload.level_id,
        question_text=question,
        language=payload.language,
        status="ANSWERED_BY_AI",
        sync_status="SYNCED",
    )

    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    if cached_answer:
        cached_answer.hit_count += 1

        db_ai_answer = AIAnswer(
            question_id=db_question.id,
            answer_text=cached_answer.answer_text,
            language=payload.language,
            confidence_score=90.0,
            model_used=f"{settings.OPENAI_MODEL}:cache",
            sources_used={"cache": True},
        )

        db.add(db_ai_answer)

        usage.request_count += 1

        db.commit()

        return {
            "answer": cached_answer.answer_text,
            "cached": True,
            "remaining_requests": daily_limit - usage.request_count,
        }

    try:
        subject = db.query(Subject).filter(Subject.id == payload.subject_id).first() if payload.subject_id else None
        level = db.query(Level).filter(Level.id == payload.level_id).first() if payload.level_id else None
        answer = ask_ai(
            question,
            subject_name=subject.name_fr if subject else None,
            level_name=level.name_fr if level else None,
            language=payload.language,
            mode=payload.mode,
        )

    except HTTPException:
        db_question.status = "REQUESTED_TEACHER"
        db_question.teacher_requested = True

        student_notification = Notification(
            user_id=current_user.id,
            title="Question transmise",
            message="Votre question a été transmise à un enseignant.",
            language=payload.language,
            type="QUESTION_SENT_TO_TEACHER",
        )

        db.add(student_notification)
        background_tasks.add_task(
            websocket_manager.send_to_user,
            current_user.id,
            {
                "type": "QUESTION_SENT_TO_TEACHER",
                "title": "Question transmise",
                "message": "Votre question a été transmise à un enseignant.",
                "question_id": str(db_question.id),
            }
        )

        matching_teachers = []

        if payload.subject_id:
            matching_teachers = teacher_subject.get_matching_teachers(
                db=db,
                subject_id=payload.subject_id,
            )

        for item in matching_teachers:
            teacher_notification = Notification(
                user_id=item.teacher_id,
                title="Nouvelle question élève",
                message="Une question liée à votre matière attend une réponse.",
                language=payload.language,
                type="NEW_STUDENT_QUESTION",
            )

            db.add(teacher_notification)

            background_tasks.add_task(
                websocket_manager.send_to_user,
                item.teacher_id,
                {
                    "type": "NEW_STUDENT_QUESTION",
                    "title": "Nouvelle question élève",
                    "message": "Une question liée à votre matière attend une réponse.",
                    "question_id": str(db_question.id),
                    "subject_id": str(payload.subject_id) if payload.subject_id else None,
                }
            )

        db.commit()

        return {
            "answer": "L’IA est temporairement indisponible ou votre quota est atteint. Votre question a été transmise à un enseignant.",
            "cached": False,
            "remaining_requests": 0,
        }

    db_ai_answer = AIAnswer(
        question_id=db_question.id,
        answer_text=answer,
        language=payload.language,
        confidence_score=80.0,
        model_used=settings.OPENAI_MODEL,
        sources_used={"cache": False},
    )

    db_cache = AICache(
        question_hash=question_hash,
        question_text=question,
        answer_text=answer,
        language=payload.language,
        model_used=settings.OPENAI_MODEL,
        hit_count=0,
    )

    db.add(db_ai_answer)
    db.add(db_cache)

    usage.request_count += 1

    db.commit()

    return {
        "answer": answer,
        "cached": False,
        "remaining_requests": daily_limit - usage.request_count,
    }


@router.post("/generate/exercises", response_model=AIChatResponse)
def generate_exercises(
    payload: AIGenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    prompt = (
        f"Génère {payload.count} exercices progressifs sur: {payload.topic}. "
        f"Difficulté: {payload.difficulty}. Inclure corrigés courts et méthode."
    )
    answer = ask_ai(prompt, language=payload.language, mode="EXERCISE_GENERATION")
    return {"answer": answer, "cached": False, "remaining_requests": 0}


@router.post("/generate/revision-sheet", response_model=AIChatResponse)
def generate_revision_sheet(
    payload: AIGenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    prompt = (
        f"Crée une fiche de révision premium sur: {payload.topic}. "
        "Structure: notions clés, erreurs fréquentes, méthode, mini quiz, plan de révision."
    )
    answer = ask_ai(prompt, language=payload.language, mode="REVISION_SHEET")
    return {"answer": answer, "cached": False, "remaining_requests": 0}


@router.post("/generate/quiz", response_model=AIChatResponse)
def generate_quiz_plan(
    payload: AIGenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    prompt = (
        f"Crée un quiz pédagogique de {payload.count} questions sur: {payload.topic}. "
        "Chaque question doit inclure 4 choix, la bonne réponse et une explication."
    )
    answer = ask_ai(prompt, language=payload.language, mode="QUIZ_GENERATION")
    return {"answer": answer, "cached": False, "remaining_requests": 0}
