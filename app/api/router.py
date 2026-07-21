from fastapi import APIRouter
from app.api.routes import uploads
from app.api.routes import ai
from app.api.routes import teacher_subjects
from app.api.routes import teacher_questions
from app.api.routes import teacher_answers
from app.api.routes import student_answers
from app.api.routes import admin_dashboard
from app.api.routes import websocket
from app.api.routes import quizzes
from app.api.routes import adaptive_learning
from app.api.routes import gamification
from app.api.routes import study_planner
from app.api.routes import content_progress
from app.api.routes import payments
from app.api.routes import statistics
from app.api.routes import chat

from app.api.routes import auth, users, schools, education, contents, questions, notifications, sync

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(schools.router, prefix="/schools", tags=["Schools"])
api_router.include_router(education.router, prefix="/education", tags=["Education"])
api_router.include_router(contents.router, prefix="/contents", tags=["Contents"])
api_router.include_router(questions.router, prefix="/questions", tags=["Questions"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(sync.router, prefix="/sync", tags=["Sync"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(
    teacher_subjects.router,
    prefix="/teacher-subjects",
    tags=["Teacher Subjects"]
)
api_router.include_router(
    teacher_questions.router,
    prefix="/teacher-questions",
    tags=["Teacher Questions"]
)
api_router.include_router(
    teacher_answers.router,
    prefix="/teacher-answers",
    tags=["Teacher Answers"]
)
api_router.include_router(
    student_answers.router,
    prefix="/student-answers",
    tags=["Student Answers"]
)
api_router.include_router(
    admin_dashboard.router,
    prefix="/admin",
    tags=["Admin Dashboard"]
)

api_router.include_router(
    websocket.router,
    tags=["WebSocket"]
)

api_router.include_router(
    quizzes.router,
    prefix="/quizzes",
    tags=["Quizzes"]
)

api_router.include_router(
    adaptive_learning.router,
    prefix="/adaptive",
    tags=["Adaptive Learning"]
)

api_router.include_router(
    gamification.router,
    prefix="/gamification",
    tags=["Gamification"]
)

api_router.include_router(
    study_planner.router,
    prefix="/study-planner",
    tags=["Study Planner"]
)

api_router.include_router(
    content_progress.router,
    prefix="/content-progress",
    tags=["Content Progress"]
)

api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"]
)

api_router.include_router(
    statistics.router,
    prefix="/statistics",
    tags=["Statistics"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"]
)


