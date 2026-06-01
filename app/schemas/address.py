from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class AddressCreate(BaseModel):
    country: str = "Cameroon"
    region: str | None = None
    city: str | None = None
    quarter: str | None = None
    details: str | None = None


class AddressResponse(ORMBaseSchema):
    id: UUID
    country: str
    region: str | None
    city: str | None
    quarter: str | None
    details: str | None
    created_at: datetime