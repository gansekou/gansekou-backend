from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse


class FirebaseLoginRequest(BaseModel):
    id_token: str

    preferred_language: str = "FR"
    role: str = "ELEVE"

    device_id: str | None = None
    device_name: str | None = None
    platform: str = "web"


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

    device_id: str | None = None
    device_name: str | None = None
    platform: str = "web"


class AuthResponse(BaseModel):
    access_type: str = "firebase"
    is_new_user: bool
    user: UserResponse

    refresh_token: str | None = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_type: str = "firebase"
    user: UserResponse
    refresh_token: str
