from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GANSECOU"
    APP_ENV: str = "development"
    DATABASE_URL: str
    SECRET_KEY: str = "change-me"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    UPLOAD_DIR: str = "uploads"
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_CREDENTIALS_JSON: str | None = None
    FIREBASE_PROJECT_ID: str | None = None
    FIREBASE_CLIENT_EMAIL: str | None = None
    FIREBASE_PRIVATE_KEY: str | None = None
    FIREBASE_STORAGE_BUCKET: str | None = None
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "deepseek-chat"
    OPENAI_BASE_URL: str = "https://api.deepseek.com"
    CAMPAY_BASE_URL: str = "https://demo.campay.net/api"
    CAMPAY_APP_ID: str | None = None
    CAMPAY_TOKEN: str | None = None
    CAMPAY_WEBHOOK_KEY: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
