import uuid
from sqlalchemy import String, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    firebase_uid: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(20), nullable=True)

    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)

    age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    role: Mapped[str] = mapped_column(String(30), default="ELEVE")

    address_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("addresses.id"), nullable=True)
    school_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=True)
    level_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("levels.id"), nullable=True)

    profile_url: Mapped[str | None] = mapped_column(String, nullable=True)
    proof_url: Mapped[str | None] = mapped_column(String, nullable=True)

    preferred_language: Mapped[str] = mapped_column(String(5), default="FR")

    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    address = relationship("Address")
    school = relationship("School")
    level = relationship("Level")

    teacher_subjects = relationship(
        "TeacherSubject",
        back_populates="teacher",
        cascade="all, delete-orphan"
    )

    chat_conversations = relationship(
        "ChatConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="check_email_or_phone_required"),
    )

    

    
