from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMBaseSchema

GANSEKOU_ROLES = {
    "ELEVE",
    "ENSEIGNANT_EN_ATTENTE",
    "ENSEIGNANT",
    "ADMIN",
    "ADMINISTRATEUR",
    "PROMOTEUR",
}

ADMIN_ROLES = {"ADMIN", "ADMINISTRATEUR", "PROMOTEUR"}


class UserCreate(BaseModel):
    firebase_uid: str

    nom: str
    prenom: str

    genre: str | None = None

    email: EmailStr | None = None
    phone: str | None = None

    age: int | None = None

    role: str = "ELEVE"

    address_id: UUID | None = None
    school_id: UUID | None = None
    level_id: UUID | None = None

    preferred_language: str = "FR"


class UserResponse(ORMBaseSchema):
    id: UUID

    firebase_uid: str

    nom: str
    prenom: str

    genre: str | None

    email: str | None
    phone: str | None

    age: int | None

    role: str

    address_id: UUID | None
    school_id: UUID | None
    level_id: UUID | None

    preferred_language: str
    status: str

    profile_url: str | None
    proof_url: str | None

    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    nom: str | None = None
    prenom: str | None = None

    genre: str | None = None

    phone: str | None = None

    age: int | None = None

    address_id: UUID | None = None
    school_id: UUID | None = None
    level_id: UUID | None = None

    preferred_language: str | None = None

    profile_url: str | None = None


class UserProfileUpdate(BaseModel):
    level_id: UUID | None = None
    school_id: UUID | None = None
    preferred_language: str | None = None
    profile_url: str | None = None


class TeacherApplicationCreate(BaseModel):
    subject_ids: list[UUID]
    proof_url: str
    message: str | None = None


class TeacherApplicationResponse(BaseModel):
    user: UserResponse
    teacher_subjects: list[dict]


class AdminRoleUpdate(BaseModel):
    role: str
