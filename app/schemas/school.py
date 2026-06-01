from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class SchoolCreate(BaseModel):
    name: str
    type: str | None = None
    address_id: UUID | None = None


class SchoolResponse(ORMBaseSchema):
    id: UUID
    name: str
    type: str | None
    address_id: UUID | None
    created_at: datetime