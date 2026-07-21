import uuid

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user

from app.models.chat_conversation import ChatConversation

from app.services.chat_service import (
    create_conversation,
    send_message,
)


router = APIRouter()


@router.post("/start")
def start_chat(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    conversation = create_conversation(
        db,
        current_user.id,
        current_user.preferred_language,
    )

    return {
        "id": str(conversation.id)
    }



@router.post("/{conversation_id}/message")
def chat_message(
    conversation_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    conversation = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == current_user.id,
        )
        .first()
    )


    message = send_message(
        db,
        conversation,
        payload["message"],
    )


    return {
        "answer": message.content
    }
