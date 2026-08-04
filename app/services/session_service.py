import secrets
import hashlib
from datetime import datetime, timedelta, timezone


def create_refresh_token() -> str:
    """
    Génère un token aléatoire sécurisé.
    """
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    """
    Stocke uniquement le hash en base.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def get_session_expiration(days: int = 30):
    """
    Expiration par défaut : 30 jours.
    """
    return datetime.now(timezone.utc) + timedelta(days=days)
