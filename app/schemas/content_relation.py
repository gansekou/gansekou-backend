from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ContentRelationCreate(BaseModel):
    child_content_id: UUID
    relation_type: str = "HAS_EXERCISE"


class ContentRelationResponse(BaseModel):
    id: UUID
    parent_content_id: UUID
    child_content_id: UUID
    relation_type: str
    created_at: datetime

    class Config:
        from_attributes = True
