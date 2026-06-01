from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class ContentTranslationCreate(BaseModel):
    content_id: UUID
    language: str
    title: str
    description: str | None = None


class ContentTranslationResponse(ORMBaseSchema):
    id: UUID
    content_id: UUID

    language: str
    title: str
    description: str | None

    created_at: datetime
    updated_at: datetime