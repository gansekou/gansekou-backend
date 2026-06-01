import uuid

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class QuizChoice(Base):
    __tablename__ = "quiz_choices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quiz_questions.id"),
        nullable=False,
        index=True
    )

    choice_text: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    question = relationship("QuizQuestion", back_populates="choices")
