from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.content_access import normalize_content_type
from app.schemas.common import ORMBaseSchema
from app.schemas.content_translation import ContentTranslationResponse


class ContentCreate(BaseModel):
    author_id: UUID
    subject_id: UUID

    level_ids: list[UUID] = Field(
        default_factory=list
    )

    specialty_ids: list[UUID] = Field(
        default_factory=list
    )

    content_type: str

    related_content_ids: list[UUID] = Field(
        default_factory=list
    )

    file_url: str | None = None
    thumbnail_url: str | None = None

    status: str = "PENDING"
    is_premium: bool = False

    is_available_offline: bool = False
    version: int = 1

    @field_validator("content_type")
    @classmethod
    def validate_content_type(
        cls,
        value: str,
    ) -> str:
        return normalize_content_type(value)


class ContentResponse(ORMBaseSchema):
    id: UUID

    author_id: UUID
    subject_id: UUID

    level_ids: list[UUID] = Field(
        default_factory=list
    )

    specialty_ids: list[UUID] = Field(
        default_factory=list
    )

    title: str | None = None

    translations: list[
        ContentTranslationResponse
    ] = Field(
        default_factory=list
    )

    content_type: str

    file_url: str | None = None
    thumbnail_url: str | None = None

    status: str
    is_premium: bool

    is_available_offline: bool
    version: int

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_relation_ids(
        cls,
        data: Any,
    ):
        """
        Transforme les relations SQLAlchemy :

            content.levels
                -> level_ids

            content.specialties
                -> specialty_ids

        afin que l'API puisse continuer à retourner
        directement les identifiants.
        """

        # ----------------------------------------------------
        # Objet SQLAlchemy
        # ----------------------------------------------------

        if hasattr(data, "levels"):

            levels = getattr(
                data,
                "levels",
                None,
            )

            specialties = getattr(
                data,
                "specialties",
                None,
            )

            return {
                "id": data.id,
                "author_id": data.author_id,
                "subject_id": data.subject_id,

                "level_ids": [
                    level.id
                    for level in (levels or [])
                ],

                "specialty_ids": [
                    specialty.id
                    for specialty in (specialties or [])
                ],

                "title": getattr(
                    data,
                    "title",
                    None,
                ),

                "translations": getattr(
                    data,
                    "translations",
                    [],
                ),

                "content_type": data.content_type,

                "file_url": getattr(
                    data,
                    "file_url",
                    None,
                ),

                "thumbnail_url": getattr(
                    data,
                    "thumbnail_url",
                    None,
                ),

                "status": data.status,
                "is_premium": data.is_premium,

                "is_available_offline": (
                    data.is_available_offline
                ),

                "version": data.version,

                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }

        return data
