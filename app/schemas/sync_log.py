from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class SyncLogCreate(BaseModel):
    user_id: UUID
    device_session_id: UUID | None = None

    entity_type: str
    entity_id: UUID | None = None

    action: str
    status: str = "SUCCESS"

    payload: dict | None = None
    error_message: str | None = None


class SyncLogResponse(ORMBaseSchema):
    id: UUID

    user_id: UUID
    device_session_id: UUID | None

    entity_type: str
    entity_id: UUID | None

    action: str
    status: str

    payload: dict | None
    error_message: str | None

    created_at: datetime