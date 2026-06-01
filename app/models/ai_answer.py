import uuid

from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import Base


class AIAnswer(Base):
    __tablename__ = "ai_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_questions.id"),
        nullable=False,
        index=True
    )

    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="FR")

    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    sources_used: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    response_type: Mapped[str] = mapped_column(
        String(30),
        default="TEXT"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    question = relationship("StudentQuestion")