import uuid

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class StudentQuestion(Base):
    __tablename__ = "student_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id"),
        nullable=True,
        index=True
    )

    level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("levels.id"),
        nullable=True
    )

    question_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    question_image_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    language: Mapped[str] = mapped_column(
        String(5),
        default="FR"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_AI",
        index=True
    )

    teacher_requested: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    assigned_teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    answered_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Offline / sync
    created_offline: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    local_temp_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    sync_status: Mapped[str] = mapped_column(
        String(30),
        default="SYNCED"
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

    student = relationship(
        "User",
        foreign_keys=[student_id]
    )

    subject = relationship("Subject")

    level = relationship("Level")

    assigned_teacher = relationship(
        "User",
        foreign_keys=[assigned_teacher_id]
    )