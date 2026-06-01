import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class TeacherAnswer(Base):
    __tablename__ = "teacher_answers"

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

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    attachment_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    language: Mapped[str] = mapped_column(
        String(5),
        default="FR"
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="PUBLISHED",
        index=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    question = relationship(
        "StudentQuestion"
    )

    teacher = relationship(
        "User",
        foreign_keys=[teacher_id]
    )