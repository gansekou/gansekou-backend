from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user_subscription import UserSubscription


def user_has_active_subscription(db: Session, user_id) -> bool:
    subscription = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "ACTIVE",
            UserSubscription.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    return subscription is not None


def require_premium_access(db: Session, user_id):
    if not user_has_active_subscription(db, user_id):
        raise HTTPException(
            status_code=403,
            detail="Abonnement premium requis"
        )