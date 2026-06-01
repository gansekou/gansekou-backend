import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class StudyPlanItem(Base):
    __tablename__ = "study_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    study_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("study_plans.id"), nullable=False, index=True)

    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True, index=True)
    level_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("levels.id"), nullable=True, index=True)
    content_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=True, index=True)
    quiz_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    item_type: Mapped[str] = mapped_column(String(50), default="CONTENT", index=True)
    skill_name: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)

    priority: Mapped[str] = mapped_column(String(30), default="NORMAL", index=True)

    estimated_minutes: Mapped[int] = mapped_column(Integer, default=20)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scheduled_for: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    study_plan = relationship("StudyPlan")
    subject = relationship("Subject")
    level = relationship("Level")
    content = relationship("Content")
    quiz = relationship("Quiz")