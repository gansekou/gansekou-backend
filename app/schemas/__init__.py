from app.schemas.address import AddressCreate, AddressResponse
from app.schemas.school import SchoolCreate, SchoolResponse
from app.schemas.education_cycle import EducationCycleCreate, EducationCycleResponse
from app.schemas.level import LevelCreate, LevelResponse
from app.schemas.specialty import SpecialtyCreate, SpecialtyResponse
from app.schemas.subject import SubjectCreate, SubjectResponse
from app.schemas.user import UserCreate, UserResponse

from app.schemas.content import ContentCreate, ContentResponse
from app.schemas.content_translation import ContentTranslationCreate, ContentTranslationResponse
from app.schemas.student_question import StudentQuestionCreate, StudentQuestionResponse
from app.schemas.ai_answer import AIAnswerCreate, AIAnswerResponse
from app.schemas.teacher_answer import TeacherAnswerCreate, TeacherAnswerResponse
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.schemas.device_session import DeviceSessionCreate, DeviceSessionResponse
from app.schemas.sync_log import SyncLogCreate, SyncLogResponse
from app.schemas.auth import FirebaseLoginRequest, AuthResponse