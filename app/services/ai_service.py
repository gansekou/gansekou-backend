from openai import OpenAI
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    RateLimitError,
)

from fastapi import HTTPException

from app.core.config import settings

# =========================
# OPENAI / DEEPSEEK CLIENT
# =========================

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Tu es Kouma IA, l'assistant pédagogique premium de Gansekou.

Tu aides les élèves camerounais du secondaire et du supérieur.

Règles importantes :
- Réponds en français ou en anglais selon la langue de l'élève.
- Explique simplement et pédagogiquement.
- Utilise une méthode claire étape par étape.
- Adapte les réponses au niveau scolaire.
- Encourage l'élève.
- Sois précis et concis.
- Pour les mathématiques :
  * détaille les calculs,
  * montre les étapes,
  * vérifie le résultat final.
- Ne génère jamais de contenu dangereux ou inapproprié.
"""

# =========================
# CONFIGURATION IA
# =========================

MAX_QUESTION_LENGTH = 1500

DEFAULT_TEMPERATURE = 0.2

DEFAULT_MAX_TOKENS = 500

# =========================
# MAIN AI FUNCTION
# =========================


def ask_ai(
    question: str,
    *,
    language: str = "FR",
) -> str:

    # =========================
    # VALIDATIONS
    # =========================

    if not question:
        raise HTTPException(
            status_code=400,
            detail="La question est obligatoire.",
        )

    question = question.strip()

    if len(question) < 3:
        raise HTTPException(
            status_code=400,
            detail="Question trop courte.",
        )

    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="Question trop longue.",
        )

    try:

        # =========================
        # AI REQUEST
        # =========================

        context = f"""
        Langue : {language}
        
        Question :
        
        {question}
        
        Consignes :
        
        - Réponds clairement.
        - Détecte automatiquement la matière concernée.
        - Adapte automatiquement ton niveau d'explication.
        - Explique étape par étape lorsque c'est nécessaire.
        - Donne un exemple si cela aide à comprendre.
        """

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": context,
                },
            ],
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        # =========================
        # EXTRACTION REPONSE
        # =========================

        answer = response.choices[0].message.content

        if not answer:
            raise HTTPException(
                status_code=500,
                detail="Réponse IA vide.",
            )

        return answer.strip()

    # =========================
    # AUTHENTICATION
    # =========================

    except AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Clé API IA invalide.",
        )

    # =========================
    # QUOTA / BILLING
    # =========================

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Quota IA dépassé.",
        )

    # =========================
    # NETWORK ERRORS
    # =========================

    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Impossible de contacter le serveur IA.",
        )

    # =========================
    # PROVIDER ERRORS
    # =========================

    except APIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur fournisseur IA : {str(e)}",
        )

    # =========================
    # UNKNOWN ERRORS
    # =========================

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur IA interne : {str(e)}",
        )
