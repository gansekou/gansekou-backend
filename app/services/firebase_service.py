import json

import firebase_admin
from firebase_admin import credentials, auth

from app.core.config import settings


def _firebase_credentials():
    if settings.FIREBASE_CREDENTIALS_JSON:
        return credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS_JSON))

    if settings.FIREBASE_PROJECT_ID and settings.FIREBASE_CLIENT_EMAIL and settings.FIREBASE_PRIVATE_KEY:
        private_key = settings.FIREBASE_PRIVATE_KEY.replace("\\n", "\n")
        return credentials.Certificate(
            {
                "type": "service_account",
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key": private_key,
                "client_email": settings.FIREBASE_CLIENT_EMAIL,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )

    if settings.FIREBASE_CREDENTIALS_PATH:
        return credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)

    raise RuntimeError(
        "Firebase credentials are not configured. Set FIREBASE_CREDENTIALS_JSON, "
        "FIREBASE_PROJECT_ID/FIREBASE_CLIENT_EMAIL/FIREBASE_PRIVATE_KEY, or "
        "FIREBASE_CREDENTIALS_PATH."
    )


def initialize_firebase():
    if not firebase_admin._apps:
        options = {}
        if settings.FIREBASE_STORAGE_BUCKET:
            options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET
        firebase_admin.initialize_app(_firebase_credentials(), options)


def verify_firebase_token(id_token: str):
    initialize_firebase()
    return auth.verify_id_token(id_token)
