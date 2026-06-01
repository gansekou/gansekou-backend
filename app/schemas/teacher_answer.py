from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class TeacherAnswerCreate(BaseModel):
    question_id: UUID
    teacher_id: UUID

    answer_text: str
    attachment_url: str | None = None

    language: str = "FR"
    status: str = "PUBLISHED"


class TeacherAnswerResponse(ORMBaseSchema):
    id: UUID

    question_id: UUID
    teacher_id: UUID

    answer_text: str
    attachment_url: str | None

    language: str
    status: str

    created_at: datetime