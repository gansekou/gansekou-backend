import logging

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.chat_message import ChatMessage


logger = logging.getLogger(__name__)


# Nombre de messages récents envoyés directement à l'IA
RECENT_MESSAGES_LIMIT = 12


# Taille maximale du contexte IA
MAX_CONTEXT_CHARS = 12000


# Taille max d'un message individuel
MAX_MESSAGE_CHARS = 2000



def clean_text(
    text: str,
    max_chars: int = MAX_MESSAGE_CHARS
):
    """
    Nettoyage et réduction des messages
    """

    if not text:
        return ""

    text = text.strip()

    if len(text) <= max_chars:
        return text


    return (
        text[:max_chars]
        +
        "\n...[suite ignorée pour la mémoire IA]"
    )





def get_recent_messages(
    db: Session,
    conversation_id,
):
    """
    Récupère les derniers messages
    """

    messages = (

        db.query(ChatMessage)

        .filter(
            ChatMessage.conversation_id
            ==
            conversation_id
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

    return messages






def build_memory_context(
    db: Session,
    conversation_id,
):
    """
    Construit la mémoire envoyée à Kouma IA
    """

    messages = get_recent_messages(
        db,
        conversation_id
    )


    context = ""

    total = 0


    for msg in messages:


        content = clean_text(
            msg.content
        )


        block = (

            f"{msg.role}: "
            f"{content}\n\n"

        )


        if (
            total + len(block)
            >
            MAX_CONTEXT_CHARS
        ):

            break


        context += block

        total += len(block)


    return context






def summarize_old_memory(
    messages
):
    """
    Préparation future :
    résumé intelligent des anciens messages.

    Ici on garde la structure
    pour brancher une IA de résumé plus tard.
    """

    if not messages:
        return ""


    summary = []


    for msg in messages:

        summary.append(
            clean_text(
                msg.content,
                500
            )
        )


    return "\n".join(summary)
