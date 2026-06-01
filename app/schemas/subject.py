from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class SubjectCreate(BaseModel):
    level_id: UUID
    specialty_id: UUID | None = None

    name_fr: str
    name_en: str

    coefficient: int = 1


class SubjectResponse(ORMBaseSchema):
    id: UUID

    level_id: UUID
    specialty_id: UUID | None

    name_fr: str
    name_en: str

    coefficient: int

    created_at: datetime