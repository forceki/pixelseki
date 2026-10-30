import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.storage import resolve_url
from app.features.creations.models import CreationCategory, CreationStatus


class CreationCreate(BaseModel):
    description: str
    category: CreationCategory = CreationCategory.other
    direction: str = "none"
    width: int = 64
    height: int = 64
    transparent_bg: bool = False
    provider: str | None = None


class RegenerateCreationRequest(BaseModel):
    description: str | None = None


class CreationResponse(BaseModel):
    id: uuid.UUID
    user_id: int
    description: str
    category: CreationCategory
    direction: str
    width: int
    height: int
    transparent_bg: bool
    provider: str
    version: int
    parent_id: uuid.UUID | None
    reference_image_url: str | None
    original_image_url: str | None
    output_image_url: str | None
    status: CreationStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("reference_image_url", "original_image_url", "output_image_url", mode="before")
    @classmethod
    def _resolve(cls, v: str | None) -> str | None:
        return resolve_url(v) if v else v
