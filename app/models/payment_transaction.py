import uuid
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=True, index=True)

    provider: Mapped[str] = mapped_column(String(50), default="CAMPAY", index=True)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)  # MTN / ORANGE

    external_reference: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)

    phone_number: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_xaf: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="XAF")

    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)

    provider_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    plan = relationship("SubscriptionPlan")