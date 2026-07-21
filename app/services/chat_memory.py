import logging

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.chat_message import ChatMessage


logger = logging.getLogger(__name__)


RECENT_MESSAGES_LIMIT = 6

MAX_CONTEXT_CHARS = 8000

MAX_MESSAGE_CHARS = 1200



def clean_message(text: str):

    if not text:
        return ""

    text = text.strip()

    if len(text) <= MAX_MESSAGE_CHARS:
        return text

    return text[:MAX_MESSAGE_CHARS] + "\n...[tronqué]"





def build_memory_context(
    db: Session,
    conversation_id
):


    messages = (

        db.query(ChatMessage)

        .filter(
            ChatMessage.conversation_id == conversation_id
        )

        .order_by(
            desc(ChatMessage.created_at)
        )

        .limit(
            RECENT_MESSAGES_LIMIT
        )

        .all()

    )


    messages.reverse()



    context = ""

    total = 0


    for msg in messages:


        content = clean_message(
            msg.content
        )


        block = (
            f"{msg.role}: {content}\n\n"
        )


        if total + len(block) > MAX_CONTEXT_CHARS:
            break


        context += block

        total += len(block)



    return context
