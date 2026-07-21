import uuid
import logging

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from fastapi import HTTPException


from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage


from app.services.ai_service import ask_ai
from app.services.chat_memory import build_memory_context


from app.core.config import settings



logger = logging.getLogger(__name__)




MAX_USER_MESSAGE_LENGTH = 10000





# =====================================================
# CREATION CONVERSATION
# =====================================================


def create_conversation(
    db: Session,
    user_id: uuid.UUID,
    language="FR",
    title="Nouvelle discussion"
):


    conversation = ChatConversation(

        user_id=user_id,

        language=language,

        title=title,

        last_message_at=datetime.now(
            timezone.utc
        )

    )


    db.add(conversation)

    db.commit()

    db.refresh(conversation)


    return conversation





# =====================================================
# ENVOI MESSAGE
# =====================================================


def send_message(
    db: Session,
    conversation: ChatConversation,
    message: str
):


    if not message or not message.strip():

        raise HTTPException(
            400,
            "Message vide"
        )



    if len(message) > MAX_USER_MESSAGE_LENGTH:

        raise HTTPException(
            400,
            "Votre message est trop volumineux."
        )



    try:


        # -----------------------------
        # MESSAGE UTILISATEUR
        # -----------------------------


        user_message = ChatMessage(

            conversation_id=conversation.id,

            role="USER",

            content=message.strip()

        )


        db.add(user_message)

        db.flush()



        # -----------------------------
        # MEMOIRE INTELLIGENTE
        # -----------------------------


        memory = build_memory_context(

            db,

            conversation.id

        )




        # -----------------------------
        # PROMPT KOUMA
        # -----------------------------


        prompt = f"""

Tu es Kouma IA,
assistant pédagogique officiel de GANSEKOU.


Tu aides les élèves camerounais.


Règles :

- Explique simplement.
- Adapte au niveau scolaire.
- Montre les étapes.
- Encourage l'élève.
- Ne donne jamais uniquement la réponse.


Historique de la discussion :

{memory}



Question actuelle :

{message}



Réponds maintenant.
"""



        # -----------------------------
        # APPEL IA
        # -----------------------------


        answer = ask_ai(

            prompt,

            language=conversation.language

        )



        if not answer:

            raise Exception(
                "Réponse IA vide"
            )




        # -----------------------------
        # REPONSE IA
        # -----------------------------


        ai_message = ChatMessage(

            conversation_id=conversation.id,

            role="ASSISTANT",

            content=answer,

            model=settings.OPENAI_MODEL

        )


        db.add(ai_message)



        conversation.last_message_at = datetime.now(
            timezone.utc
        )



        db.commit()


        db.refresh(ai_message)



        return ai_message




    except HTTPException:

        raise




    except Exception as e:


        db.rollback()


        logger.exception(
            "Erreur chat conversation=%s",
            conversation.id
        )


        raise HTTPException(

            status_code=500,

            detail=(
                "Kouma IA rencontre "
                "un problème temporaire."
            )

        )







# =====================================================
# HISTORIQUE UTILISATEUR
# =====================================================


def get_conversation_messages(
    db: Session,
    conversation_id
):


    return (

        db.query(ChatMessage)

        .filter(
            ChatMessage.conversation_id
            ==
            conversation_id
        )

        .order_by(
            ChatMessage.created_at.asc()
        )

        .all()

    )
