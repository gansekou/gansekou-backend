import uuid
import hashlib
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user
from app.services.ai_service import ask_ai
from app.core.config import settings

from app.models.ai_cache import AICache

from app.models.student_question import StudentQuestion
from app.models.ai_answer import AIAnswer



router = APIRouter()


class AIChatRequest(BaseModel):
    question: str
    language: str = "FR"


class AIChatResponse(BaseModel):
    answer: str
    cached: bool
    


class AIGenerationRequest(BaseModel):
    topic: str
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



@router.post("/chat", response_model=AIChatResponse)
def ai_chat(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    question = payload.question.strip()

    if len(question) < 3:
        raise HTTPException(
            status_code=400,
            detail="Question trop courte",
        )

    question_hash = make_question_hash(question, payload.language)

    cached_answer = (
        db.query(AICache)
        .filter(AICache.question_hash == question_hash)
        .first()
    )

    db_question = StudentQuestion(
        student_id=current_user.id,
        subject_id=None,
        level_id=None,
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


        db.commit()

        return {
            "answer": cached_answer.answer_text,
            "cached": True,
        }

    try:
        
        answer = ask_ai(
            question,
            language=payload.language,
        )

    except HTTPException as e:
        raise e

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

    db.commit()

    return {
        "answer": answer,
        "cached": False,
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
    answer = ask_ai(
        prompt,
        language=payload.language,
    )
    return {"answer": answer, "cached": False }


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
    answer = ask_ai(
        prompt,
        language=payload.language,
    )
    return {"answer": answer, "cached": False}


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
    answer = ask_ai(
        prompt,
        language=payload.language,
    )
    return {"answer": answer, "cached": False}
