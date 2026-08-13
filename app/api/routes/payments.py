import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import get_current_user
from app.core.config import settings

from app.models.user import User
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription
from app.models.payment_transaction import PaymentTransaction

from app.services.monetbil_service import monetbil_service


router = APIRouter()


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class PaymentInitRequest(BaseModel):
    plan_id: uuid.UUID
    phone_number: str | None = None


# ============================================================
# HELPERS
# ============================================================

def normalize_period(
    period: str | None,
    duration_days: int,
) -> str:

    if period:
        normalized = period.lower()

        if normalized in ["month", "year"]:
            return normalized

    if duration_days >= 330:
        return "year"

    return "month"


def normalize_payment_status(
    status: str | None,
) -> str:

    if not status:
        return "PENDING"

    normalized = str(status).lower().strip()

    if normalized in [
        "success",
        "successful",
        "completed",
    ]:
        return "SUCCESS"

    if normalized in [
        "failed",
        "cancelled",
        "canceled",
    ]:
        return "FAILED"

    return "PENDING"


# ============================================================
# SUBSCRIPTION
# ============================================================

def activate_subscription(
    db: Session,
    user_id,
    plan: SubscriptionPlan,
):
    now = datetime.now(timezone.utc)

    old_subscriptions = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "ACTIVE",
        )
        .all()
    )

    for subscription in old_subscriptions:
        subscription.status = "EXPIRED"

    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan.id,
        status="ACTIVE",
        starts_at=now,
        expires_at=now + timedelta(
            days=plan.duration_days
        ),
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


def activate_subscription_once(
    db: Session,
    transaction: PaymentTransaction,
    plan: SubscriptionPlan,
):
    if transaction.status == "SUCCESS":
        return None

    transaction.status = "SUCCESS"

    return activate_subscription(
        db,
        transaction.user_id,
        plan,
    )


# ============================================================
# DEFAULT PLANS
# ============================================================

def ensure_default_subscription_plans(
    db: Session,
):

    defaults = [
        {
            "code": "EXCELLENCE_MONTH",
            "name": "Gansekou Excellence",
            "price_xaf": 500,
            "duration_days": 30,
            "period": "month",
            "description": (
                "La formule idéale pour progresser "
                "chaque mois sans limitation."
            ),
        },
        {
            "code": "EXCELLENCE_YEAR",
            "name": "Gansekou Excellence+",
            "price_xaf": 4500,
            "duration_days": 365,
            "period": "year",
            "description": (
                "La formule annuelle pour les élèves ambitieux."
            ),
        },
    ]

    changed = False

    for item in defaults:

        plan = (
            db.query(SubscriptionPlan)
            .filter(
                SubscriptionPlan.code == item["code"]
            )
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


# ============================================================
# ADMIN - CREATE PLAN
# ============================================================

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

    if current_user.role not in [
        "ADMIN",
        "PROMOTEUR",
        "ADMINISTRATEUR",
    ]:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à l'administration",
        )

    if price_xaf <= 0:
        raise HTTPException(
            status_code=400,
            detail="Le prix doit être supérieur à zéro",
        )

    if duration_days <= 0:
        raise HTTPException(
            status_code=400,
            detail="La durée doit être supérieure à zéro",
        )

    existing = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.code == code
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Un plan avec ce code existe déjà",
        )

    plan = SubscriptionPlan(
        code=code,
        name=name,
        price_xaf=price_xaf,
        duration_days=duration_days,
        period=normalize_period(
            period,
            duration_days,
        ),
        description=description,
        is_active=True,
        is_premium=True,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan


# ============================================================
# GET PLANS
# ============================================================

@router.get("/plans")
def get_subscription_plans(
    db: Session = Depends(get_db),
):

    ensure_default_subscription_plans(db)

    return (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.is_active == True
        )
        .order_by(
            SubscriptionPlan.price_xaf.asc()
        )
        .all()
    )


# ============================================================
# INIT MONETBIL PAYMENT
# ============================================================

@router.post("/init")
async def init_payment(
    payload: PaymentInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # PLAN
    # ========================================================

    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id == payload.plan_id,
            SubscriptionPlan.is_active == True,
        )
        .first()
    )

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan introuvable",
        )

    # ========================================================
    # AMOUNT
    # ========================================================

    amount = plan.price_xaf

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Le prix du plan est invalide",
        )

    # ========================================================
    # PHONE
    # ========================================================

    normalized_phone = None

    if payload.phone_number:

        normalized_phone = (
            monetbil_service.normalize_cameroon_phone(
                payload.phone_number
            )
        )

        if not normalized_phone:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Numéro camerounais invalide. "
                    "Utilisez par exemple 6XXXXXXXX."
                ),
            )

    # ========================================================
    # REFERENCE
    # ========================================================

    external_reference = (
        f"GANSEKOU-{uuid.uuid4()}"
    )

    # ========================================================
    # LOCAL TRANSACTION
    # ========================================================

    transaction = PaymentTransaction(
        user_id=current_user.id,
        plan_id=plan.id,
        provider="MONETBIL",
        payment_method="MONETBIL",
        external_reference=external_reference,
        phone_number=normalized_phone,
        amount_xaf=amount,
        currency="XAF",
        status="PENDING",
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # ========================================================
    # USER INFO
    # ========================================================

    user_id = str(current_user.id)

    first_name = getattr(
        current_user,
        "first_name",
        None,
    )

    last_name = getattr(
        current_user,
        "last_name",
        None,
    )

    email = getattr(
        current_user,
        "email",
        None,
    )

    # ========================================================
    # MONETBIL
    # ========================================================

    result = await monetbil_service.create_payment(
        amount=amount,
        payment_ref=external_reference,
        user=user_id,
        item_ref=str(plan.id),
        phone=payload.phone_number,
        first_name=first_name,
        last_name=last_name,
        email=email,
        notify_url=settings.MONETBIL_NOTIFY_URL,
    )

        # ========================================================
        # INIT FAILED
        # ========================================================
    
        if not result["success"]:
    
            transaction.status = "FAILED"
            transaction.provider_response = result
    
            db.commit()
    
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "Impossible d'initialiser "
                        "le paiement Monetbil"
                    ),
                    "monetbil_response": result,
                },
            )
    
        # ========================================================
        # MONETBIL PAYMENT ID
        # ========================================================
    
        payment_id = result.get("payment_id")
    
        if not payment_id:
    
            transaction.status = "FAILED"
            transaction.provider_response = result
    
            db.commit()
    
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "Monetbil n'a pas retourné "
                        "de paymentId"
                    ),
                    "monetbil_response": result,
                },
            )
    
        # ========================================================
        # SAVE MONETBIL PAYMENT ID
        # ========================================================
    
        transaction.monetbil_payment_id = str(payment_id)
        transaction.provider_response = result
    
        db.commit()
        db.refresh(transaction)

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "message": (
            "Paiement initialisé. "
            "Redirection vers Monetbil."
        ),
        "transaction_id": str(transaction.id),
        "external_reference": (
            transaction.external_reference
        ),
        "status": transaction.status,
        "amount_xaf": transaction.amount_xaf,
        "currency": transaction.currency,
        "monetbil_payment_id": transaction.monetbil_payment_id,
        "monetbil_status": result.get("status"),
        "channel": result.get("channel"),
        "channel_name": result.get("channel_name"),
        "channel_ussd": result.get("channel_ussd"),
        "plan": {
            "id": str(plan.id),
            "code": plan.code,
            "name": plan.name,
            "price_xaf": plan.price_xaf,
            "duration_days": plan.duration_days,
            "period": plan.period,
        },
    }

# ============================================================
# MY TRANSACTIONS
# ============================================================

@router.get("/transactions/me")
def get_my_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.user_id
            == current_user.id
        )
        .order_by(
            PaymentTransaction.created_at.desc()
        )
        .all()
    )


# ============================================================
# MY SUBSCRIPTION
# ============================================================

@router.get("/subscription/me")
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    subscription = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id
            == current_user.id,

            UserSubscription.status
            == "ACTIVE",

            UserSubscription.expires_at
            > datetime.now(timezone.utc),
        )
        .order_by(
            UserSubscription.expires_at.desc()
        )
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


# ============================================================
# MONETBIL WEBHOOK
# ============================================================

@router.post("/webhook/monetbil")
async def monetbil_webhook(
    request: Request,
    db: Session = Depends(get_db),
):

    # ========================================================
    # READ PAYLOAD
    # ========================================================

    payload: dict[str, Any] = {}

    try:

        content_type = (
            request.headers.get(
                "content-type",
                "",
            )
            .lower()
        )

        if "application/json" in content_type:

            body = await request.json()

            if isinstance(body, dict):
                payload.update(body)

        elif (
            "application/x-www-form-urlencoded"
            in content_type
        ):

            form = await request.form()

            payload.update(dict(form))

        else:

            form = await request.form()

            if form:
                payload.update(dict(form))

    except Exception:

        pass

    # ========================================================
    # QUERY PARAMETERS
    # ========================================================

    for key, value in request.query_params.items():

        if key not in payload:
            payload[key] = value

    # ========================================================
    # EXTRACT
    # ========================================================

    service = payload.get("service")

    payment_ref = payload.get("payment_ref")

    transaction_id = payload.get(
        "transaction_id"
    )

    transaction_uuid = payload.get(
        "transaction_uuid"
    )

    monetbil_status = payload.get("status")

    amount = payload.get("amount")

    currency = payload.get("currency")

    country_iso = payload.get("country_iso")

    # ========================================================
    # VALIDATE SERVICE
    # ========================================================

    expected_service = (
        settings.MONETBIL_SERVICE_KEY
    )

    if not service:

        raise HTTPException(
            status_code=403,
            detail="Service Monetbil manquant",
        )

    if service != expected_service:

        raise HTTPException(
            status_code=403,
            detail="Service Monetbil invalide",
        )

    # ========================================================
    # PAYMENT REF
    # ========================================================

    if not payment_ref:

        raise HTTPException(
            status_code=400,
            detail="payment_ref manquant",
        )

    # ========================================================
    # FIND TRANSACTION
    # ========================================================

    transaction = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.external_reference
            == payment_ref
        )
        .first()
    )

    if not transaction:

        raise HTTPException(
            status_code=404,
            detail="Transaction introuvable",
        )

    # ========================================================
    # IDEMPOTENCY
    # ========================================================

    if transaction.status == "SUCCESS":

        return {
            "message": "Transaction déjà traitée",
            "status": "SUCCESS",
            "transaction_id": str(
                transaction.id
            ),
        }

    # ========================================================
    # VALIDATE AMOUNT
    # ========================================================

    if amount is not None:

        try:

            received_amount = int(
                float(amount)
            )

        except (
            TypeError,
            ValueError,
        ):

            raise HTTPException(
                status_code=400,
                detail="Montant Monetbil invalide",
            )

        if (
            received_amount
            != transaction.amount_xaf
        ):

            transaction.provider_response = {
                "error": "Montant différent",
                "received": amount,
                "expected": (
                    transaction.amount_xaf
                ),
                "payload": payload,
            }

            db.commit()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Montant du paiement invalide"
                ),
            )

    # ========================================================
    # VALIDATE CURRENCY
    # ========================================================

    if (
        currency
        and str(currency).upper() != "XAF"
    ):

        raise HTTPException(
            status_code=400,
            detail="Devise invalide",
        )

    # ========================================================
    # VALIDATE COUNTRY
    # ========================================================

    if (
        country_iso
        and str(country_iso).upper() != "CM"
    ):

        raise HTTPException(
            status_code=400,
            detail="Pays de paiement invalide",
        )

    # ========================================================
    # PLAN
    # ========================================================

    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.id
            == transaction.plan_id
        )
        .first()
    )

    if not plan:

        raise HTTPException(
            status_code=404,
            detail="Plan associé introuvable",
        )

    # ========================================================
    # SAVE PROVIDER RESPONSE
    # ========================================================

    transaction.provider_response = {
        "webhook": payload,
        "monetbil": {
            "transaction_id": transaction_id,
            "transaction_uuid": transaction_uuid,
        },
    }

    # ========================================================
    # STATUS
    # ========================================================

    normalized_status = (
        normalize_payment_status(
            monetbil_status
        )
    )

    # ========================================================
    # SUCCESS
    # ========================================================

    if normalized_status == "SUCCESS":

        activate_subscription_once(
            db=db,
            transaction=transaction,
            plan=plan,
        )

    # ========================================================
    # FAILED
    # ========================================================

    elif normalized_status == "FAILED":

        transaction.status = "FAILED"

    # ========================================================
    # PENDING / UNKNOWN
    # ========================================================

    else:

        transaction.status = "PENDING"

    # ========================================================
    # COMMIT
    # ========================================================

    db.commit()
    db.refresh(transaction)

    return {
        "message": "Webhook Monetbil traité",
        "status": transaction.status,
        "transaction_id": str(
            transaction.id
        ),
        "monetbil_transaction_id": (
            transaction_id
        ),
    }


# ============================================================
# MANUAL STATUS CHECK
# ============================================================

@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    transaction = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.id == transaction_id,
            PaymentTransaction.user_id
            == current_user.id,
        )
        .first()
    )

    if not transaction:

        raise HTTPException(
            status_code=404,
            detail="Transaction introuvable",
        )

    return transaction
