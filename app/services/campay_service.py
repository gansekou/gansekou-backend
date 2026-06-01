import httpx

from app.core.config import settings


class CamPayService:
    def __init__(self):
        self.base_url = settings.CAMPAY_BASE_URL
        self.token = settings.CAMPAY_TOKEN

    def headers(self):
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

    async def collect_payment(
        self,
        amount: int,
        phone_number: str,
        description: str,
        external_reference: str,
    ):
        payload = {
            "amount": str(amount),
            "currency": "XAF",
            "from": phone_number,
            "description": description,
            "external_reference": external_reference,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/collect/",
                json=payload,
                headers=self.headers(),
            )

        if response.status_code >= 400:
            return {
                "success": False,
                "status_code": response.status_code,
                "data": response.text,
            }

        return {
            "success": True,
            "data": response.json(),
        }

    async def check_transaction_status(self, reference: str):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/transaction/{reference}/",
                headers=self.headers(),
            )

        if response.status_code >= 400:
            return {
                "success": False,
                "status_code": response.status_code,
                "data": response.text,
            }

        return {
            "success": True,
            "data": response.json(),
        }


campay_service = CamPayService()