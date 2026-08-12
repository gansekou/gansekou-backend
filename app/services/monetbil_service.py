from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class MonetbilService:
    BASE_URL = "https://api.monetbil.com/widget/v2.1"

    def __init__(self) -> None:
        self.service_key = settings.MONETBIL_SERVICE_KEY
        self.service_secret = settings.MONETBIL_SERVICE_SECRET

    async def create_payment(
        self,
        *,
        amount: int,
        payment_ref: str,
        user: str,
        item_ref: str,
        phone: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        return_url: str | None = None,
        notify_url: str | None = None,
        operator: str | None = None,
    ) -> dict[str, Any]:

        if not self.service_key:
            return {
                "success": False,
                "error": "MONETBIL_SERVICE_KEY non configurée",
            }

        if amount <= 0:
            return {
                "success": False,
                "error": "Le montant doit être supérieur à zéro",
            }

        payload: dict[str, Any] = {
            "amount": amount,
            "currency": "XAF",
            "country": "CM",
            "locale": "fr",
            "payment_ref": payment_ref,
            "user": user,
            "item_ref": item_ref,
        }

        if phone:
            payload["phone"] = phone
            payload["phone_lock"] = True

        if first_name:
            payload["first_name"] = first_name

        if last_name:
            payload["last_name"] = last_name

        if email:
            payload["email"] = email

        if return_url:
            payload["return_url"] = return_url

        if notify_url:
            payload["notify_url"] = notify_url

        if operator:
            payload["operator"] = operator

        url = f"{self.BASE_URL}/{self.service_key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                data = {
                    "raw_response": response.text,
                }

            if response.status_code >= 400:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": data,
                }

            if not data.get("success"):
                return {
                    "success": False,
                    "response": data,
                }

            return {
                "success": True,
                "payment_url": data.get("payment_url"),
                "data": data,
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Délai dépassé lors de la connexion à Monetbil",
            }

        except httpx.HTTPError as exc:
            return {
                "success": False,
                "error": f"Erreur HTTP Monetbil: {str(exc)}",
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"Erreur Monetbil: {str(exc)}",
            }


monetbil_service = MonetbilService()
