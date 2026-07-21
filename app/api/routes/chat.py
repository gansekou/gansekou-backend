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


@router.get(
    "/{conversation_id}",
    tags=["Chat"]
)
def get_chat_history(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):

    conversation = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == current_user.id
        )
        .first()
    )


    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation introuvable."
        )


    messages = get_conversation_messages(
        db,
        conversation_id
    )


    return [
        {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "image_url": message.image_url,
            "sources": message.sources,
            "model": message.model,
            "created_at": message.created_at,
        }
        for message in messages
    ]
