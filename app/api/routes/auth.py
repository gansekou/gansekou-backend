from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.firebase_service import verify_firebase_token
from app.schemas.auth import FirebaseLoginRequest, EmailRegisterRequest, AuthResponse
from app.schemas.user import UserCreate
from app.crud.user import user

router = APIRouter()

SELF_REGISTER_ROLES = {"ELEVE"}


def validate_self_register_role(role: str):
    normalized_role = role.strip().upper()

    if normalized_role not in SELF_REGISTER_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Ce rôle ne peut pas être choisi à l'inscription",
        )
    return normalized_role


@router.post("/firebase-login", response_model=AuthResponse)
def firebase_login(payload: FirebaseLoginRequest, db: Session = Depends(get_db)):
    try:
        decoded = verify_firebase_token(payload.id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token Firebase invalide")

    firebase_uid = decoded.get("uid")
    email = decoded.get("email")
    name = decoded.get("name") or ""
    picture = decoded.get("picture")

    firebase_info = decoded.get("firebase", {})
    provider = firebase_info.get("sign_in_provider")

    existing_user = user.get_by_firebase_uid(db, firebase_uid)

    if existing_user:
        return {
            "access_type": "firebase",
            "is_new_user": False,
            "user": existing_user,
        }

    existing_email = user.get_by_email(db, email) if email else None
    if existing_email:
        existing_email.firebase_uid = firebase_uid
        if picture and not existing_email.profile_url:
            existing_email.profile_url = picture
        db.commit()
        db.refresh(existing_email)
        return {
            "access_type": "firebase",
            "is_new_user": False,
            "user": existing_email,
        }

    social_providers = ["google.com", "facebook.com", "password"]

    if provider not in social_providers:
        raise HTTPException(
            status_code=403,
            detail="Compte introuvable. Veuillez créer un compte avant de vous connecter avec email/password.",
        )

    role = validate_self_register_role(payload.role)

    parts = name.split(" ", 1)
    prenom = parts[0] if len(parts) > 0 and parts[0] else "Utilisateur"
    nom = parts[1] if len(parts) > 1 else "GANSECOU"

    new_user_data = UserCreate(
        firebase_uid=firebase_uid,
        nom=nom,
        prenom=prenom,
        email=email,
        phone=None,
        role=role,
        preferred_language=payload.preferred_language,
    )

    new_user = user.create_user(db, new_user_data)

    if picture:
        new_user.profile_url = picture
        db.commit()
        db.refresh(new_user)

    return {
        "access_type": "firebase",
        "is_new_user": True,
        "user": new_user,
    }


@router.post("/register-email", response_model=AuthResponse)
def register_email(payload: EmailRegisterRequest, db: Session = Depends(get_db)):
    role = validate_self_register_role(payload.role)

    existing_uid = user.get_by_firebase_uid(db, payload.firebase_uid)
    if existing_uid:
        raise HTTPException(status_code=400, detail="Ce compte existe déjà")

    existing_email = user.get_by_email(db, payload.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")

    new_user_data = UserCreate(
        firebase_uid=payload.firebase_uid,
        nom=payload.nom,
        prenom=payload.prenom,
        genre=payload.genre,
        email=payload.email,
        phone=payload.phone,
        age=payload.age,
        role=role,
        preferred_language=payload.preferred_language,
    )

    new_user = user.create_user(db, new_user_data)

    return {
        "access_type": "firebase",
        "is_new_user": True,
        "user": new_user,
    }
