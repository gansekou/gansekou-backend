import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.session import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "chat_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role = Column(
        String(20),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    image_url = Column(
        Text,
        nullable=True,
    )

    sources = Column(
        JSON,
        nullable=True,
    )

    model = Column(
        String(100),
        nullable=True,
    )

    prompt_tokens = Column(
        Integer,
        default=0,
    )

    completion_tokens = Column(
        Integer,
        default=0,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    conversation = relationship(
        "ChatConversation",
        back_populates="messages",
    )
