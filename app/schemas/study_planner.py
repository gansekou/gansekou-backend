import uuid
from datetime import datetime
from pydantic import BaseModel


class StudyPlanGenerateRequest(BaseModel):
    title: str | None = None
    language: str = "FR"
    duration_days: int = 7
    max_items: int = 20


class StudyPlanResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    title: str
    description: str | None
    language: str
    status: str
    plan_type: str
    duration_days: int
    total_items: int
    completed_items: int
    is_ai_generated: bool
    start_date: datetime | None
    end_date: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class StudyPlanItemResponse(BaseModel):
    id: uuid.UUID
    study_plan_id: uuid.UUID
    subject_id: uuid.UUID | None
    level_id: uuid.UUID | None
    content_id: uuid.UUID | None
    quiz_id: uuid.UUID | None
    title: str
    description: str | None
    item_type: str
    skill_name: str | None
    priority: str
    estimated_minutes: int
    order_index: int
    is_completed: bool
    completed_at: datetime | None
    scheduled_for: datetime | None

    class Config:
        from_attributes = True