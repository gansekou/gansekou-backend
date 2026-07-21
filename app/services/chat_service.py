import uuid

from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastapi import HTTPException

from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage

from app.services.ai_service import ask_ai
from app.core.config import settings


MAX_HISTORY_MESSAGES = 20



# =====================================================
# CREATION CONVERSATION
# =====================================================

def create_conversation(
    db: Session,
    user_id: uuid.UUID,
    language: str = "FR",
    title: str = "Nouvelle discussion",
):

    conversation = ChatConversation(
        user_id=user_id,
        title=title,
        language=language,
        last_message_at=datetime.now(timezone.utc),
    )


    db.add(conversation)

    db.commit()

    db.refresh(conversation)

    return conversation





# =====================================================
# ENVOI MESSAGE CHAT
# =====================================================

def send_message(
    db: Session,
    conversation: ChatConversation,
    message: str,
):

    if not message or len(message.strip()) < 2:

        raise HTTPException(
            status_code=400,
            detail="Message vide ou trop court."
        )


    try:


        # =================================================
        # 1 - MESSAGE ELEVE
        # =================================================

        user_message = ChatMessage(
            conversation_id=conversation.id,
            role="USER",
            content=message.strip(),
        )


        db.add(user_message)

        db.flush()



        # =================================================
        # 2 - RECUPERATION HISTORIQUE
        # =================================================

        history = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.conversation_id == conversation.id
            )
            .order_by(
                desc(ChatMessage.created_at)
            )
            .limit(MAX_HISTORY_MESSAGES)
            .all()
        )


        history.reverse()



        conversation_context = "\n\n".join(
            [
                f"{msg.role}: {msg.content}"
                for msg in history
            ]
        )




        # =================================================
        # 3 - PROMPT KOUMA IA
        # =================================================

        prompt = f"""

Tu es Kouma IA, assistant pédagogique premium de GANSEKOU.

Tu accompagnes les élèves camerounais dans leurs apprentissages.

Tes domaines :

- Mathématiques
- Sciences
- Langues
- Histoire-Géographie
- Méthodes de travail
- Orientation scolaire
- Préparation aux examens

Consignes :

- Adapte toujours ton niveau d'explication à l'élève.
- Explique progressivement.
- Donne des exemples simples.
- Encourage l'élève.
- Ne donne pas uniquement la réponse, explique le raisonnement.


Historique :

{conversation_context}


Réponds au dernier message de l'élève.

"""




        # =================================================
        # 4 - APPEL IA
        # =================================================

        answer = ask_ai(
            prompt,
            language=conversation.language,
        )




        # =================================================
        # 5 - REPONSE IA
        # =================================================

        ai_message = ChatMessage(
            conversation_id=conversation.id,
            role="ASSISTANT",
            content=answer,
            model=settings.OPENAI_MODEL,
        )


        db.add(ai_message)

        db.flush()



        # =================================================
        # 6 - MISE A JOUR CONVERSATION
        # =================================================

        conversation.last_message_at = datetime.now(timezone.utc)


        db.commit()


        db.refresh(ai_message)


        return ai_message



    except Exception as e:

        db.rollback()


        raise HTTPException(
            status_code=500,
            detail=f"Erreur chat IA : {str(e)}"
        )





# =====================================================
# HISTORIQUE CONVERSATION
# =====================================================

def get_conversation_messages(
    db: Session,
    conversation_id: uuid.UUID,
):

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation_id
        )
        .order_by(
            ChatMessage.created_at.asc()
        )
        .all()
    )


    return messages
