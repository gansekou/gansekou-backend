from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class AIAnswerCreate(BaseModel):
    question_id: UUID
    answer_text: str
    language: str = "FR"

    confidence_score: float | None = None
    model_used: str | None = None
    sources_used: dict | None = None


class AIAnswerResponse(ORMBaseSchema):
    id: UUID
    question_id: UUID

    answer_text: str
    language: str

    confidence_score: float | None
    model_used: str | None
    sources_used: dict | None

    created_at: datetime