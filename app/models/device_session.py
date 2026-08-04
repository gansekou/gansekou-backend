import uuid

from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class DeviceSession(Base):
    __tablename__ = "device_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    # Identification appareil
    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    platform: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )  # android / ios / web / desktop


    # Authentification session longue durée
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    last_activity: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    expires_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )


    # Synchronisation offline
    last_synced_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )


    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


    user = relationship(
        "User"
    )
