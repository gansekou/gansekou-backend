from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class MonetbilService:
    BASE_URL = "https://api.monetbil.com/payment/v1"

    def __init__(self) -> None:
        self.service_key = settings.MONETBIL_SERVICE_KEY

    async def place_payment(
        self,
        *,
        amount: int,
        phonenumber: str,
        payment_ref: str,
        item_ref: str,
        user: str,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        operator: str | None = None,
        notify_url: str | None = None,
    ) -> dict[str, Any]:

        # --------------------------------------------------
        # Validation configuration
        # --------------------------------------------------

        if not self.service_key:
            return {
                "success": False,
                "error": "MONETBIL_SERVICE_KEY non configurée",
            }

        # --------------------------------------------------
        # Validation montant
        # --------------------------------------------------

        if amount <= 0:
            return {
                "success": False,
                "error": "Le montant doit être supérieur à zéro",
            }

        # --------------------------------------------------
        # Validation téléphone
        # --------------------------------------------------

        if not phonenumber:
            return {
                "success": False,
                "error": "Le numéro de téléphone est obligatoire",
            }

        # --------------------------------------------------
        # Payload Monetbil Payment API v1
        # --------------------------------------------------

        payload: dict[str, Any] = {
            "service": self.service_key,
            "phonenumber": phonenumber,
            "amount": str(amount),
            "currency": "XAF",
            "country": "CM",
            "payment_ref": payment_ref,
            "item_ref": item_ref,
        }

        # --------------------------------------------------
        # Champs optionnels
        # --------------------------------------------------

        if operator:
            payload["operator"] = operator

        if user:
            payload["user"] = user

        if first_name:
            payload["first_name"] = first_name

        if last_name:
            payload["last_name"] = last_name

        if email:
            payload["email"] = email

        if notify_url:
            payload["notify_url"] = notify_url

        # --------------------------------------------------
        # Appel API
        # --------------------------------------------------

        url = f"{self.BASE_URL}/placePayment"

        try:

            async with httpx.AsyncClient(
                timeout=30.0
            ) as client:

                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )

            # --------------------------------------------------
            # Lecture réponse
            # --------------------------------------------------

            try:
                data = response.json()

            except Exception:

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Réponse Monetbil non JSON",
                    "raw_response": response.text,
                }

            # --------------------------------------------------
            # Erreur HTTP
            # --------------------------------------------------

            if response.status_code >= 400:

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": data,
                }

            # --------------------------------------------------
            # Monetbil status
            # --------------------------------------------------

            status = str(
                data.get("status", "")
            ).upper()

            if status != "REQUEST_ACCEPTED":

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": data,
                    "error": data.get(
                        "message",
                        "Monetbil a refusé la demande de paiement",
                    ),
                }

            # --------------------------------------------------
            # paymentId
            # --------------------------------------------------

            payment_id = data.get("paymentId")

            if not payment_id:

                return {
                    "success": False,
                    "response": data,
                    "error": (
                        "Monetbil a accepté la demande "
                        "mais aucun paymentId n'a été retourné"
                    ),
                }

            return {
                "success": True,
                "payment_id": str(payment_id),
                "status": status,
                "message": data.get("message"),
                "channel": data.get("channel"),
                "channel_name": data.get("channel_name"),
                "channel_ussd": data.get("channel_ussd"),
                "data": data,
            }

        except httpx.TimeoutException:

            return {
                "success": False,
                "error": (
                    "Délai dépassé lors de la connexion à Monetbil"
                ),
            }

        except httpx.HTTPError as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur HTTP Monetbil: {str(exc)}"
                ),
            }

        except Exception as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur Monetbil: {str(exc)}"
                ),
            }


    async def check_payment(
        self,
        *,
        payment_id: str,
    ) -> dict[str, Any]:

        if not payment_id:
            return {
                "success": False,
                "error": "paymentId manquant",
            }

        url = f"{self.BASE_URL}/checkPayment"

        payload = {
            "paymentId": payment_id,
        }

        try:

            async with httpx.AsyncClient(
                timeout=30.0
            ) as client:

                response = await client.post(
                    url,
                    data=payload,
                    headers={
                        "Accept": "application/json",
                    },
                )

            try:
                data = response.json()

            except Exception:

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Réponse Monetbil non JSON",
                    "raw_response": response.text,
                }

            if response.status_code >= 400:

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": data,
                }

            transaction = data.get("transaction")

            if transaction:

                monetbil_status = transaction.get(
                    "status"
                )

            else:

                monetbil_status = None

            return {
                "success": True,
                "payment_id": str(
                    data.get(
                        "paymentId",
                        payment_id,
                    )
                ),
                "message": data.get("message"),
                "transaction": transaction,
                "monetbil_status": monetbil_status,
                "data": data,
            }

        except httpx.TimeoutException:

            return {
                "success": False,
                "error": (
                    "Délai dépassé lors de la vérification "
                    "du paiement Monetbil"
                ),
            }

        except httpx.HTTPError as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur HTTP Monetbil: {str(exc)}"
                ),
            }

        except Exception as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur Monetbil: {str(exc)}"
                ),
            }


monetbil_service = MonetbilService()
