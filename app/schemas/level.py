from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class LevelCreate(BaseModel):
    cycle_id: UUID | None = None

    name_fr: str
    name_en: str

    order_index: int


class LevelResponse(ORMBaseSchema):
    id: UUID
    cycle_id: UUID | None

    name_fr: str
    name_en: str

    order_index: int
    created_at: datetime