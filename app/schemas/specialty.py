from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class SpecialtyCreate(BaseModel):
    name_fr: str
    name_en: str

    description_fr: str | None = None
    description_en: str | None = None


class SpecialtyResponse(ORMBaseSchema):
    id: UUID

    name_fr: str
    name_en: str

    description_fr: str | None
    description_en: str | None

    created_at: datetime