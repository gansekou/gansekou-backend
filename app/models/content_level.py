import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ContentLevel(Base):
    __tablename__ = "content_levels"

    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contents.id", ondelete="CASCADE"),
        primary_key=True,
    )

    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("levels.id", ondelete="CASCADE"),
        primary_key=True,
    )
