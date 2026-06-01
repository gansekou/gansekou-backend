from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class EducationCycleCreate(BaseModel):
    name_fr: str
    name_en: str


class EducationCycleResponse(ORMBaseSchema):
    id: UUID
    name_fr: str
    name_en: str
    created_at: datetime