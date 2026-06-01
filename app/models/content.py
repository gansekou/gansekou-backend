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


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
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

    specialty_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("specialties.id"),
        nullable=True,
        index=True
    )

    # COURSE / QUIZ / EXAM / PDF / VIDEO / AUDIO
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    # DRAFT / PUBLISHED / ARCHIVED
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        index=True
    )

    file_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    video_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    audio_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    external_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    estimated_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    difficulty_level: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_premium: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_downloadable: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    is_available_offline: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    allow_comments: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    allow_ai_summary: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    total_views: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    total_downloads: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    total_likes: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    total_shares: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    average_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    published_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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

    specialty = relationship("Specialty")