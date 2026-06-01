from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse


class FirebaseLoginRequest(BaseModel):
    id_token: str
    preferred_language: str = "FR"
    role: str = "ELEVE"


class EmailRegisterRequest(BaseModel):
    firebase_uid: str

    nom: str
    prenom: str

    email: EmailStr
    phone: str | None = None

    genre: str | None = None
    age: int | None = None

    preferred_language: str = "FR"
    role: str = "ELEVE"


class AuthResponse(BaseModel):
    access_type: str = "firebase"
    is_new_user: bool
    user: UserResponse