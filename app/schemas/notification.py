from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class NotificationCreate(BaseModel):
    user_id: UUID

    title: str
    message: str

    language: str = "FR"
    type: str | None = None
    data: dict | None = None


class NotificationResponse(ORMBaseSchema):
    id: UUID
    user_id: UUID

    title: str
    message: str

    language: str
    type: str | None
    data: dict | None

    is_read: bool
    sync_status: str

    created_at: datetime
