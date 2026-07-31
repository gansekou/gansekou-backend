# app/models/content_relation.py

import uuid

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class ContentRelation(Base):
    __tablename__ = "content_relations"

    __table_args__ = (
        UniqueConstraint(
            "parent_content_id",
            "child_content_id",
            "relation_type",
            name="uq_content_relation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    parent_content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    child_content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relation_type: Mapped[str] = mapped_column(
        String(50),
        default="HAS_EXERCISE",
        nullable=False,
        index=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    parent_content = relationship(
        "Content",
        foreign_keys=[parent_content_id],
        back_populates="child_relations",
    )

    child_content = relationship(
        "Content",
        foreign_keys=[child_content_id],
        back_populates="parent_relations",
    )
