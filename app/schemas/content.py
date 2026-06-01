from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, field_validator

from app.schemas.common import ORMBaseSchema
from app.core.content_access import normalize_content_type


class ContentCreate(BaseModel):
    author_id: UUID
    subject_id: UUID
    level_id: UUID
    specialty_id: UUID | None = None

    content_type: str
    file_url: str | None = None
    thumbnail_url: str | None = None

    status: str = "PENDING"
    is_premium: bool = False

    is_available_offline: bool = False
    version: int = 1

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        return normalize_content_type(value)


class ContentResponse(ORMBaseSchema):
    id: UUID

    author_id: UUID
    subject_id: UUID
    level_id: UUID
    specialty_id: UUID | None

    content_type: str
    file_url: str | None
    thumbnail_url: str | None

    status: str
    is_premium: bool

    is_available_offline: bool
    version: int

    created_at: datetime
    updated_at: datetime
