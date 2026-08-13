from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import settings


class MonetbilService:
    """
    Service d'intégration avec l'API Monetbil Payment v1.

    Documentation :
    POST /payment/v1/placePayment
    POST /payment/v1/checkPayment
    """

    BASE_URL = "https://api.monetbil.com/payment/v1"

    def __init__(self) -> None:
        self.service_key = settings.MONETBIL_SERVICE_KEY

    # ============================================================
    # PHONE NUMBER
    # ============================================================

    @staticmethod
    def normalize_cameroon_phone(
        phone: str | None,
    ) -> str | None:
        """
        Normalise un numéro camerounais au format international
        attendu par Monetbil.

        Exemples acceptés :
            654123456
            0654123456
            237654123456
            +237654123456

        Retour :
            237654123456

        Retourne None si le numéro est invalide.
        """

        if not phone:
            return None

        # Supprimer espaces, tirets, parenthèses, etc.
        cleaned = re.sub(
            r"[\s\-\(\)\.]",
            "",
            phone.strip(),
        )

        # +237XXXXXXXXX
        if cleaned.startswith("+237"):
            cleaned = cleaned[1:]

        # 00237XXXXXXXXX
        elif cleaned.startswith("00237"):
            cleaned = cleaned[2:]

        # 237XXXXXXXXX
        elif cleaned.startswith("237"):
            pass

        # 0XXXXXXXXX
        elif cleaned.startswith("0"):
            cleaned = "237" + cleaned[1:]

        # 6XXXXXXXX
        elif cleaned.startswith("6"):
            cleaned = "237" + cleaned

        else:
            return None

        # Un numéro camerounais doit avoir :
        # 237 + 9 chiffres
        if not re.fullmatch(
            r"2376\d{8}",
            cleaned,
        ):
            return None

        return cleaned

    # ============================================================
    # PLACE PAYMENT
    # ============================================================

    async def create_payment(
        self,
        *,
        amount: int,
        payment_ref: str,
        user: str,
        item_ref: str,
        phone: str,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        return_url: str | None = None,
        notify_url: str | None = None,
        operator: str | None = None,
    ) -> dict[str, Any]:

        # --------------------------------------------------------
        # Validation
        # --------------------------------------------------------

        if not self.service_key:
            return {
                "success": False,
                "error": (
                    "MONETBIL_SERVICE_KEY "
                    "non configurée"
                ),
            }

        if amount <= 0:
            return {
                "success": False,
                "error": (
                    "Le montant doit être "
                    "supérieur à zéro"
                ),
            }

        if not phone:
            return {
                "success": False,
                "error": (
                    "Le numéro de téléphone "
                    "est obligatoire"
                ),
            }

        # --------------------------------------------------------
        # Normalisation téléphone
        # --------------------------------------------------------

        normalized_phone = (
            self.normalize_cameroon_phone(phone)
        )

        if not normalized_phone:
            return {
                "success": False,
                "error": (
                    "Numéro camerounais invalide"
                ),
            }

        # --------------------------------------------------------
        # Payload Monetbil Payment API v1
        # --------------------------------------------------------

        payload: dict[str, Any] = {
            "service": self.service_key,
            "phonenumber": normalized_phone,
            "amount": str(amount),
            "country": "CM",
            "currency": "XAF",
            "payment_ref": payment_ref,
            "item_ref": item_ref,
            "user": user,
        }

        if notify_url:
            payload["notify_url"] = notify_url

        if operator:
            payload["operator"] = operator

        if first_name:
            payload["first_name"] = first_name

        if last_name:
            payload["last_name"] = last_name

        if email:
            payload["email"] = email

        # --------------------------------------------------------
        # Appel Monetbil
        # --------------------------------------------------------

        url = (
            f"{self.BASE_URL}/placePayment"
        )

        try:

            async with httpx.AsyncClient(
                timeout=30.0
            ) as client:

                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": (
                            "application/json"
                        ),
                    },
                )

            # ----------------------------------------------------
            # Lecture réponse
            # ----------------------------------------------------

            try:

                data = response.json()

            except Exception:

                return {
                    "success": False,
                    "status_code": (
                        response.status_code
                    ),
                    "error": (
                        "Réponse Monetbil "
                        "non JSON"
                    ),
                    "raw_response": (
                        response.text
                    ),
                }

            # ----------------------------------------------------
            # Erreur HTTP
            # ----------------------------------------------------

            if response.status_code >= 400:

                return {
                    "success": False,
                    "status_code": (
                        response.status_code
                    ),
                    "response": data,
                }

            # ----------------------------------------------------
            # Statut Monetbil
            # ----------------------------------------------------

            monetbil_status = str(
                data.get("status", "")
            ).upper().strip()

            if monetbil_status != (
                "REQUEST_ACCEPTED"
            ):

                return {
                    "success": False,
                    "status_code": (
                        response.status_code
                    ),
                    "response": data,
                }

            # ----------------------------------------------------
            # paymentId
            # ----------------------------------------------------

            payment_id = data.get(
                "paymentId"
            )

            if not payment_id:

                return {
                    "success": False,
                    "status_code": (
                        response.status_code
                    ),
                    "error": (
                        "Monetbil a accepté "
                        "la requête mais aucun "
                        "paymentId n'a été retourné"
                    ),
                    "response": data,
                }

            # ----------------------------------------------------
            # Succès initial
            # ----------------------------------------------------

            return {
                "success": True,
                "payment_id": str(
                    payment_id
                ),
                "status": data.get(
                    "status"
                ),
                "message": data.get(
                    "message"
                ),
                "channel": data.get(
                    "channel"
                ),
                "channel_name": data.get(
                    "channel_name"
                ),
                "channel_ussd": data.get(
                    "channel_ussd"
                ),
                "data": data,
            }

        except httpx.TimeoutException:

            return {
                "success": False,
                "error": (
                    "Délai dépassé lors de "
                    "la connexion à Monetbil"
                ),
            }

        except httpx.HTTPError as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur HTTP Monetbil: "
                    f"{str(exc)}"
                ),
            }

        except Exception as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur Monetbil: "
                    f"{str(exc)}"
                ),
            }

    # ============================================================
    # CHECK PAYMENT
    # ============================================================

    async def check_payment(
        self,
        *,
        payment_id: str,
    ) -> dict[str, Any]:

        if not self.service_key:
            return {
                "success": False,
                "error": (
                    "MONETBIL_SERVICE_KEY "
                    "non configurée"
                ),
            }

        if not payment_id:
            return {
                "success": False,
                "error": (
                    "paymentId manquant"
                ),
            }

        payload = {
            "paymentId": str(
                payment_id
            ),
        }

        url = (
            f"{self.BASE_URL}/checkPayment"
        )

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

            # ----------------------------------------------------
            # Lecture réponse
            # ----------------------------------------------------

            try:

                data = response.json()

            except Exception:

                return {
                    "success": False,
                    "status_code": (
                        response.status_code
                    ),
                    "error": (
                        "Réponse Monetbil "
                        "non JSON"
                    ),
                    "raw_response": (
                        response.text
                    ),
                }

            # ----------------------------------------------------
            # Erreur HTTP
            # ----------------------------------------------------

            if response.status_code >= 400:

                return {
                    "success": False,
                    "status_code": (
                        response.status_code
                    ),
                    "response": data,
                }

            # ----------------------------------------------------
            # Transaction
            # ----------------------------------------------------

            transaction = data.get(
                "transaction"
            )

            if not transaction:

                return {
                    "success": True,
                    "payment_id": str(
                        payment_id
                    ),
                    "message": data.get(
                        "message"
                    ),
                    "transaction": None,
                    "data": data,
                }

            # ----------------------------------------------------
            # Statut paiement
            #
            # Monetbil :
            # 1  = Success
            # 0  = Failed
            # -1 = Cancelled
            # -2 = Refunded
            # ----------------------------------------------------

            monetbil_status = transaction.get(
                "status"
            )

            return {
                "success": True,
                "payment_id": str(
                    payment_id
                ),
                "status": monetbil_status,
                "message": transaction.get(
                    "message"
                ),
                "transaction": transaction,
                "data": data,
            }

        except httpx.TimeoutException:

            return {
                "success": False,
                "error": (
                    "Délai dépassé lors de "
                    "la connexion à Monetbil"
                ),
            }

        except httpx.HTTPError as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur HTTP Monetbil: "
                    f"{str(exc)}"
                ),
            }

        except Exception as exc:

            return {
                "success": False,
                "error": (
                    f"Erreur Monetbil: "
                    f"{str(exc)}"
                ),
            }


monetbil_service = MonetbilService()
