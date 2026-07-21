import uuid

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Integer,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "chat_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )


    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


    sources: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )


    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )


    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )


    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


    conversation = relationship(
        "ChatConversation",
        back_populates="messages",
    )
