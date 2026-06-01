import uuid

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id"),
        nullable=False,
        index=True
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    question_image_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    points: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    question_type: Mapped[str] = mapped_column(
        String(30),
        default="MULTIPLE_CHOICE"
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    quiz = relationship("Quiz", back_populates="questions")
    choices = relationship(
        "QuizChoice",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuizChoice.created_at",
    )
