import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class QuizCreate(BaseModel):
    title: str
    description: str | None = None
    course_id: uuid.UUID | None = None
    subject_id: uuid.UUID
    level_id: uuid.UUID
    language: str = "FR"
    difficulty_level: str | None = None
    quiz_type: str = "QCM"
    is_premium: bool = False
    is_randomized: bool = False
    allow_retry: bool = True
    passing_score: int = Field(default=50, ge=0, le=100)
    estimated_duration_minutes: int | None = Field(default=None, ge=1)


class QuizUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    course_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    level_id: uuid.UUID | None = None
    language: str | None = None
    difficulty_level: str | None = None
    quiz_type: str | None = None
    status: str | None = None
    is_premium: bool | None = None
    is_randomized: bool | None = None
    allow_retry: bool | None = None
    passing_score: int | None = Field(default=None, ge=0, le=100)
    estimated_duration_minutes: int | None = Field(default=None, ge=1)


class QuizChoiceCreate(BaseModel):
    choice_text: str
    is_correct: bool = False


class QuizChoiceUpdate(BaseModel):
    choice_text: str | None = None
    is_correct: bool | None = None


class QuizChoiceResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    choice_text: str
    is_correct: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class QuizChoicePublicResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    choice_text: str

    class Config:
        from_attributes = True


class QuizQuestionCreate(BaseModel):
    question_text: str
    question_image_url: str | None = None
    explanation: str | None = None
    question_type: str = "MULTIPLE_CHOICE"
    points: int = Field(default=1, ge=1)
    order_index: int = 0
    is_required: bool = True


class QuizQuestionUpdate(BaseModel):
    question_text: str | None = None
    question_image_url: str | None = None
    explanation: str | None = None
    question_type: str | None = None
    points: int | None = Field(default=None, ge=1)
    order_index: int | None = None
    is_required: bool | None = None


class QuizQuestionResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    question_text: str
    question_image_url: str | None = None
    explanation: str | None = None
    question_type: str
    points: int
    order_index: int
    is_required: bool
    created_at: datetime | None = None
    choices: list[QuizChoiceResponse] = []

    class Config:
        from_attributes = True


class QuizQuestionPublicResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    question_text: str
    question_image_url: str | None = None
    question_type: str
    points: int
    order_index: int
    is_required: bool
    choices: list[QuizChoicePublicResponse] = []

    class Config:
        from_attributes = True


class QuizResponse(QuizCreate):
    id: uuid.UUID
    content_id: uuid.UUID | None = None
    course_id: uuid.UUID | None = None
    author_id: uuid.UUID
    status: str
    total_attempts: int
    total_questions: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    questions: list[QuizQuestionPublicResponse] = []

    class Config:
        from_attributes = True


class QuizManageResponse(QuizResponse):
    questions: list[QuizQuestionResponse] = []


class QuizAttemptResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    score: int
    correct_answers: int
    total_questions: int
    is_passed: bool
    started_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class QuizSubmitPayload(BaseModel):
    answers: dict[str, str | list[str]]


class QuizAnswerResult(BaseModel):
    question_id: uuid.UUID
    selected_choice_ids: list[uuid.UUID]
    correct_choice_ids: list[uuid.UUID]
    is_correct: bool
    points: int
    earned_points: int
    explanation: str | None = None


class QuizResultResponse(BaseModel):
    quiz_id: uuid.UUID
    attempt_id: uuid.UUID
    score: int
    passed: bool
    correct_answers: int
    total_questions: int
    results: list[QuizAnswerResult]


class AIQuizGenerateRequest(BaseModel):
    course_id: uuid.UUID | None = None
    subject_id: uuid.UUID
    level_id: uuid.UUID
    title: str
    language: str = "FR"
    difficulty_level: str = "INTERMEDIATE"
    number_of_questions: int = Field(default=10, ge=1, le=50)
    topic: str | None = None
