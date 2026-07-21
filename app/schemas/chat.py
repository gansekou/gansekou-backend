from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatMessageResponse(BaseModel):

    id: UUID
    role: str
    content: str

    image_url: str | None = None

    model: str | None = None

    created_at: datetime


    model_config = ConfigDict(
        from_attributes=True
    )



class ChatHistoryResponse(BaseModel):

    id: UUID

    title: str

    language: str

    created_at: datetime

    last_message_at: datetime

    messages: list[ChatMessageResponse]


    model_config = ConfigDict(
        from_attributes=True
    )
