import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user
from app.core.config import settings

from app.models.user import User
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription
from app.models.payment_transaction import PaymentTransaction
from app.services.campay_service import campay_service

router = APIRouter()


class PaymentInitRequest(BaseModel):
    plan_id: uuid.UUID
    phone_number: str
    payment_method: str  # MTN / ORANGE


def normalize_period(period: str | None, duration_days: int) -> str:
    if period:
        normalized = period.lower()
        if normalized in ["month", "year"]:
            return normalized

    if duration_days >= 330:
        return "year"

    return "month"


def normalize_payment_status(status: str | None) -> str:
    if not status:
        return "PENDING"

    status = status.upper()

    if status in ["SUCCESSFUL", "SUCCESS", "COMPLETED"]:
        return "SUCCESS"

    if status in ["FAILED", "CANCELLED", "CANCELED"]:
        return "FAILED"

    return "PENDING"


def is_valid_webhook_secret(webhook_key: str | None, signature: str | None) -> bool:
    expected = settings.CAMPAY_WEBHOOK_KEY

    if not expected:
        return False

    return webhook_key == expected or signature == expected


def activate_subscription(db: Session, user_id, plan: SubscriptionPlan):
    now = datetime.now(timezone.utc)

    old_subs = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "ACTIVE",
        )
        .all()
    )

    for sub in old_subs:
        sub.status = "EXPIRED"

    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan.id,
        status="ACTIVE",
        starts_at=now,
        expires_at=now + timedelta(days=plan.duration_days),
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


def activate_subscription_once(db: Session, transaction: PaymentTransaction, plan: SubscriptionPlan):
    if transaction.status == "SUCCESS":
        return None

    transaction.status = "SUCCESS"
    return activate_subscription(db, transaction.user_id, plan)


def ensure_default_subscription_plans(db: Session):
    defaults = [
        {
            "code": "EXCELLENCE_MONTH",
            "name": "Gansekou Excellence",
            "price_xaf": 500,
            "duration_days": 30,
            "period": "month",
            "description": "La formule ideale pour progresser chaque mois sans limitation.",
        },
        {
            "code": "EXCELLENCE_YEAR",
            "name": "Gansekou Excellence+",
            "price_xaf": 4500,
            "duration_days": 365,
            "period": "year",
            "description": "La formule annuelle pour les eleves ambitieux.",
        },
    ]

    changed = False
    for item in defaults:
        plan = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.code == item["code"])
            .first()
        )
        if plan:
            continue

        db.add(
            SubscriptionPlan(
                code=item["code"],
                name=item["name"],
                price_xaf=item["price_xaf"],
                duration_days=item["duration_days"],
                period=item["period"],
                description=item["description"],
                is_active=True,
                is_premium=True,
            )
        )
        changed = True

    if changed:
        db.commit()


async def verify_campay_transaction(transaction: PaymentTransaction):
    reference = transaction.provider_reference or transaction.external_reference
    result = await campay_service.check_transaction_status(reference)

    if not result["success"]:
        return result, None, "PENDING"

    data = result["data"]
    return result, data, normalize_payment_status(data.get("status"))


@router.post("/plans")
def create_subscription_plan(
    code: str,
    name: str,
    price_xaf: int,
    duration_days: int,
    period: str | None = None,
    description: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]:
        raise HTTPException(403, "Accès réservé à l'administration")

    plan = SubscriptionPlan(
        code=code,
        name=name,
        price_xaf=price_xaf,
        duration_days=duration_days,
        period=normalize_period(period, duration_days),
        description=description,
        is_active=True,
        is_premium=True,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan


@router.get("/plans")
def get_subscription_plans(
    db: Session = Depends(get_db),
):
    ensure_default_subscription_plans(db)
    return (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.price_xaf.asc())
        .all()
    )


@router.post("/init")
async def init_payment(
    payload: PaymentInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == payload.plan_id,
            SubscriptionPlan.is_active == True,
        )
        .first()
    )

    if not plan:
        raise HTTPException(404, "Plan introuvable")

    method = payload.payment_method.upper()

    if method not in ["MTN", "ORANGE"]:
        raise HTTPException(400, "Méthode invalide. Utilisez MTN ou ORANGE")

    external_reference = f"GANSEKOU-{uuid.uuid4()}"

    transaction = PaymentTransaction(
        user_id=current_user.id,
        plan_id=plan.id,
        payment_method=method,
        external_reference=external_reference,
        phone_number=payload.phone_number,
        amount_xaf=plan.price_xaf,
        currency="XAF",
        status="PENDING",
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    result = await campay_service.collect_payment(
        amount=plan.price_xaf,
        phone_number=payload.phone_number,
        description=f"Abonnement Gansekou - {plan.name}",
        external_reference=external_reference,
    )

    transaction.provider_response = result

    if not result["success"]:
        transaction.status = "FAILED"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Échec initialisation paiement CamPay",
                "campay_response": result,
            }
        )

    data = result["data"]

    transaction.provider_reference = (
        data.get("reference")
        or data.get("operator_reference")
        or data.get("external_reference")
    )

    initial_status = normalize_payment_status(data.get("status"))
    transaction.status = "PENDING" if initial_status == "SUCCESS" else initial_status

    db.commit()
    db.refresh(transaction)

    return {
        "message": "Paiement initié. Confirmez sur votre téléphone.",
        "transaction_id": transaction.id,
        "external_reference": transaction.external_reference,
        "provider_reference": transaction.provider_reference,
        "status": transaction.status,
        "amount_xaf": transaction.amount_xaf,
        "currency": transaction.currency,
        "provider_response": data,
    }


@router.get("/transactions/me")
def get_my_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.user_id == current_user.id)
        .order_by(PaymentTransaction.created_at.desc())
        .all()
    )


@router.get("/subscription/me")
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status == "ACTIVE",
            UserSubscription.expires_at > datetime.now(timezone.utc),
        )
        .order_by(UserSubscription.expires_at.desc())
        .first()
    )

    if not subscription:
        return {
            "is_premium": False,
            "subscription": None,
        }

    return {
        "is_premium": True,
        "subscription": subscription,
    }


@router.post("/transactions/{transaction_id}/verify")
async def verify_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.id == transaction_id,
            PaymentTransaction.user_id == current_user.id,
        )
        .first()
    )

    if not transaction:
        raise HTTPException(404, "Transaction introuvable")

    result, data, verified_status = await verify_campay_transaction(transaction)

    if not result["success"]:
        transaction.provider_response = result
        db.commit()
        raise HTTPException(400, "Impossible de vérifier la transaction")

    transaction.provider_response = data

    if verified_status == "SUCCESS":
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == transaction.plan_id).first()

        if plan:
            activate_subscription_once(db, transaction, plan)
    else:
        transaction.status = verified_status

    db.commit()
    db.refresh(transaction)

    return {
        "transaction": transaction,
        "provider_response": data,
    }


@router.post("/webhook/campay")
async def campay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_campay_signature: str | None = Header(default=None),
):
    payload = await request.json()

    # CamPay peut envoyer une clé/signature selon la configuration.
    # Ici on vérifie aussi la présence de la webhook key si tu l'envoies en header custom.
    webhook_key = request.headers.get("X-CamPay-Webhook-Key")

    if not is_valid_webhook_secret(webhook_key, x_campay_signature):
        raise HTTPException(403, "Webhook invalide")

    reference = (
        payload.get("external_reference")
        or payload.get("reference")
        or payload.get("operator_reference")
    )

    if not reference:
        raise HTTPException(400, "Référence manquante")

    transaction = (
        db.query(PaymentTransaction)
        .filter(
            (PaymentTransaction.external_reference == reference)
            | (PaymentTransaction.provider_reference == reference)
        )
        .first()
    )

    if not transaction:
        raise HTTPException(404, "Transaction introuvable")

    result, data, verified_status = await verify_campay_transaction(transaction)

    if not result["success"]:
        transaction.provider_response = {
            "webhook_payload": payload,
            "verification": result,
        }
        db.commit()
        raise HTTPException(400, "Impossible de vÃ©rifier la transaction")

    transaction.provider_response = {
        "webhook_payload": payload,
        "verification": data,
    }

    if verified_status == "SUCCESS":
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == transaction.plan_id).first()

        if plan:
            activate_subscription_once(db, transaction, plan)
    else:
        transaction.status = verified_status

    db.commit()

    return {
        "message": "Webhook traité",
        "status": transaction.status,
    }
