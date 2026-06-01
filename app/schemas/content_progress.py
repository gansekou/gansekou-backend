import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ContentProgressUpdate(BaseModel):
    progress_percent: int = Field(ge=0, le=100)
    time_spent_minutes: int = Field(default=0, ge=0)


class ContentRatingCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review: str | None = None


class ContentProgressResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    content_id: uuid.UUID

    progress_percent: int
    time_spent_minutes: int

    is_started: bool
    is_completed: bool

    started_at: datetime | None
    completed_at: datetime | None
    last_accessed_at: datetime | None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentFavoriteResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    content_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ContentRatingResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    content_id: uuid.UUID
    rating: int
    review: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True