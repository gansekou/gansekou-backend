from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class DeviceSessionCreate(BaseModel):
    user_id: UUID

    device_id: str
    device_name: str | None = None
    platform: str | None = None


class DeviceSessionResponse(ORMBaseSchema):
    id: UUID
    user_id: UUID

    device_id: str
    device_name: str | None
    platform: str | None

    last_synced_at: datetime | None
    created_at: datetime