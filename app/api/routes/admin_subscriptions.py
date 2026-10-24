
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.user_subscription import UserSubscription

router = APIRouter()


class AdminSubscriptionActivationRequest(BaseModel):
    period: str = Field(pattern=r"^(month|year)$")


@router.post("/admin/users/{user_id}/activate-subscription")
def admin_activate_subscription(
    user_id: uuid.UUID,
    payload: AdminSubscriptionActivationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Seul le promoteur peut activer un abonnement manuellement.
    if current_user.role != "PROMOTEUR":
        raise HTTPException(
            status_code=403,
            detail="Seul le promoteur peut activer un abonnement.",
        )

    target_user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if target_user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable.",
        )

    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.is_active.is_(True),
            SubscriptionPlan.is_premium.is_(True),
            SubscriptionPlan.period == payload.period,
        )
        .order_by(SubscriptionPlan.duration_days.asc())
        .first()
    )

    if plan is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Aucun plan Premium actif pour cette période. "
                "Vérifiez les plans d’abonnement dans l’administration."
            ),
        )

    now = datetime.now(timezone.utc)

    try:
        active_subscriptions = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == target_user.id,
                UserSubscription.status == "ACTIVE",
            )
            .order_by(UserSubscription.expires_at.desc())
            .with_for_update()
            .all()
        )

        current_active = next(
            (
                subscription
                for subscription in active_subscriptions
                if subscription.expires_at > now
            ),
            None,
        )

        # Conserver un seul abonnement ACTIVE.
        for subscription in active_subscriptions:
            if subscription is not current_active:
                subscription.status = "EXPIRED"

        if current_active is not None:
            # Prolonger à partir de l'échéance actuelle.
            current_active.expires_at = (
                current_active.expires_at
                + timedelta(days=plan.duration_days)
            )
            current_active.plan_id = plan.id
            current_active.status = "ACTIVE"
            current_active.auto_renew = False

            subscription = current_active
            starts_at = current_active.starts_at

        else:
            # Aucun abonnement valide : démarrer maintenant.
            subscription = UserSubscription(
                user_id=target_user.id,
                plan_id=plan.id,
                status="ACTIVE",
                starts_at=now,
                expires_at=now + timedelta(
                    days=plan.duration_days
                ),
                auto_renew=False,
            )

            db.add(subscription)
            starts_at = now

        db.flush()
        db.refresh(subscription)

        expires_at = subscription.expires_at

        db.commit()

        return {
            "user_id": str(target_user.id),
            "period": payload.period,
            "duration_days": plan.duration_days,
            "starts_at": starts_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_premium": expires_at > now,
        }

    except Exception as exc:
        db.rollback()

        if isinstance(exc, HTTPException):
            raise

        raise HTTPException(
            status_code=500,
            detail=(
                "L’activation de l’abonnement a échoué. "
                "Aucune modification n’a été confirmée."
            ),
        ) from exc
