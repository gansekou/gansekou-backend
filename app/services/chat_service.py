import uuid

from sqlalchemy.orm import Session

from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.services.ai_service import ask_ai
from app.core.config import settings


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
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation



def send_message(
    db: Session,
    conversation: ChatConversation,
    message: str,
):

    # Message utilisateur

    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="USER",
        content=message,
    )

    db.add(user_message)
    db.commit()


    # Historique conversation

    history = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation.id
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


    context = "\n\n".join(
        [
            f"{msg.role}: {msg.content}"
            for msg in history
        ]
    )


    prompt = f"""
Voici l'historique de discussion :

{context}


Réponds au dernier message de l'élève.
"""

    answer = ask_ai(
        prompt,
        language=conversation.language,
    )


    # Réponse IA

    ai_message = ChatMessage(
        conversation_id=conversation.id,
        role="ASSISTANT",
        content=answer,
        model=settings.OPENAI_MODEL,
    )

    db.add(ai_message)

    db.commit()

    return ai_message
