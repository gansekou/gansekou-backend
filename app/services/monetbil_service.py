from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class MonetbilService:
    """
    Service d'intégration Monetbil Widget API v2.1.

    Documentation :
    https://www.monetbil.com/docs/monetbil-payment-widget-v2.1-en.pdf
    """

    BASE_URL = "https://api.monetbil.com/widget/v2.1"

    def __init__(self) -> None:
        self.service_key = settings.MONETBIL_SERVICE_KEY

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

        # ========================================================
        # VALIDATION
        # ========================================================

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

        if not payment_ref:
            return {
                "success": False,
                "error": "payment_ref manquant",
            }

        if not user:
            return {
                "success": False,
                "error": "user manquant",
            }

        if not item_ref:
            return {
                "success": False,
                "error": "item_ref manquant",
            }

        # ========================================================
        # PAYLOAD MONETBIL
        # ========================================================

        payload: dict[str, Any] = {
            "amount": amount,
            "currency": "XAF",
            "country": "CM",
            "locale": "fr",
            "payment_ref": payment_ref,
            "user": user,
            "item_ref": item_ref,
        }

        # --------------------------------------------------------
        # Téléphone
        # --------------------------------------------------------

        if phone:
            normalized_phone = self.normalize_cameroon_phone(phone)

            if normalized_phone:
                payload["phone"] = normalized_phone
                payload["phone_lock"] = True

        # --------------------------------------------------------
        # Informations utilisateur
        # --------------------------------------------------------

        if first_name:
            payload["first_name"] = first_name.strip()

        if last_name:
            payload["last_name"] = last_name.strip()

        if email:
            payload["email"] = email.strip().lower()

        # --------------------------------------------------------
        # URLs
        # --------------------------------------------------------

        if return_url:
            payload["return_url"] = return_url

        if notify_url:
            payload["notify_url"] = notify_url

        # --------------------------------------------------------
        # Opérateur
        # --------------------------------------------------------

        if operator:
            payload["operator"] = operator

        # ========================================================
        # API URL
        # ========================================================

        url = f"{self.BASE_URL}/{self.service_key}"

        try:

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=30.0,
                    write=30.0,
                    pool=10.0,
                )
            ) as client:

                response = await client.post(
                    url,
                    data=payload,
                    headers={
                        "Accept": "application/json",
                    },
                )

            # ====================================================
            # PARSE RESPONSE
            # ====================================================

            try:
                data = response.json()

            except Exception:

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": "Réponse Monetbil non JSON",
                    "raw_response": response.text[:2000],
                }

            # ====================================================
            # HTTP ERROR
            # ====================================================

            if response.status_code >= 400:

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": data,
                }

            # ====================================================
            # MONETBIL ERROR
            # ====================================================

            if not data.get("success"):

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": data,
                }

            # ====================================================
            # PAYMENT URL
            # ====================================================

            payment_url = data.get("payment_url")

            if not payment_url:

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": (
                        "Monetbil indique que le paiement "
                        "a été créé mais aucune payment_url "
                        "n'a été retournée."
                    ),
                    "response": data,
                }

            # ====================================================
            # SUCCESS
            # ====================================================

            return {
                "success": True,
                "payment_url": payment_url,
                "data": data,
            }

        except httpx.TimeoutException:

            return {
                "success": False,
                "error": (
                    "Délai dépassé lors de la connexion "
                    "à Monetbil"
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

    # ============================================================
    # PHONE NORMALIZATION
    # ============================================================

    @staticmethod
    def normalize_cameroon_phone(
        phone: str | None,
    ) -> str | None:

        if not phone:
            return None

        value = (
            phone
            .strip()
            .replace(" ", "")
            .replace("-", "")
            .replace(".", "")
            .replace("(", "")
            .replace(")", "")
        )

        # +237XXXXXXXXX
        if value.startswith("+237"):
            value = value[1:]

        # 00237XXXXXXXXX
        elif value.startswith("00237"):
            value = value[2:]

        # 6XXXXXXXX → 2376XXXXXXXX
        elif (
            len(value) == 9
            and value.startswith("6")
        ):
            value = f"237{value}"

        # 237XXXXXXXXX
        elif value.startswith("237"):
            pass

        else:
            return None

        # Un numéro camerounais international
        # doit normalement contenir 12 chiffres.
        if (
            len(value) != 12
            or not value.isdigit()
            or not value.startswith("2376")
        ):
            return None

        return value


monetbil_service = MonetbilService()
