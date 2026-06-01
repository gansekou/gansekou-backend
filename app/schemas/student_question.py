from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ORMBaseSchema


class StudentQuestionCreate(BaseModel):
    student_id: UUID | None = None
    subject_id: UUID | None = None
    level_id: UUID | None = None

    question_text: str | None = None
    question_image_url: str | None = None

    language: str = "FR"

    answer_mode: str | None = None
    requested_teacher_id: UUID | None = None

    created_offline: bool = False
    local_temp_id: str | None = None


class StudentQuestionResponse(ORMBaseSchema):
    id: UUID

    student_id: UUID
    subject_id: UUID | None
    level_id: UUID | None

    question_text: str | None
    question_image_url: str | None

    language: str

    status: str
    teacher_requested: bool
    assigned_teacher_id: UUID | None

    created_offline: bool
    local_temp_id: str | None
    sync_status: str

    created_at: datetime
    updated_at: datetime
