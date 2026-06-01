import uuid

from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    Text,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    content_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contents.id"),
        nullable=True,
        index=True
    )

    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contents.id"),
        nullable=True,
        index=True
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id"),
        nullable=False,
        index=True
    )

    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("levels.id"),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    language: Mapped[str] = mapped_column(
        String(5),
        default="FR",
        index=True
    )

    difficulty_level: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    quiz_type: Mapped[str] = mapped_column(
        String(30),
        default="QCM",
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="PUBLISHED",
        index=True
    )

    is_premium: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_randomized: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    allow_retry: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    passing_score: Mapped[int] = mapped_column(
        Integer,
        default=50
    )

    estimated_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    total_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    total_questions: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    author = relationship("User")
    subject = relationship("Subject")
    level = relationship("Level")
    content = relationship("Content", foreign_keys=[content_id])
    course = relationship("Content", foreign_keys=[course_id])
    questions = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.order_index",
    )
    attempts = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan",
    )
