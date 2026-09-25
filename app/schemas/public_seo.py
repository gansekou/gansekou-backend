from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PublicSeoContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None

    content_type: str
    content_format: str

    subject_name: str | None = None
    level_names: list[str] = []
    specialty_name: str | None = None

    thumbnail_url: str | None = None

    is_premium: bool
    published_at: datetime | None = None
