import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.storage import resolve_url
from app.features.generations.models import AssetType, CameraView, JobStatus


# ── Items ──

class GenerationItemCreate(BaseModel):
    item_index: int
    item_description: str


class GenerationItemResponse(BaseModel):
    id: uuid.UUID
    item_index: int
    item_description: str
    direction: str | None
    version: int
    tag: str
    edit_count: int
    redo_count: int
    original_image_url: str | None
    output_image_url: str | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("original_image_url", "output_image_url", mode="before")
    @classmethod
    def _resolve(cls, v: str | None) -> str | None:
        return resolve_url(v) if v else v


# ── Jobs ──

class GenerationJobCreate(BaseModel):
    asset_type: AssetType
    directions: str
    camera_view: CameraView
    pixel_size: int
    global_description: str
    style_reference_url: str | None = None
    provider: str | None = None
    items: list[GenerationItemCreate] = []


class GenerationJobUpdate(BaseModel):
    name: str | None = None


class AddItemRequest(BaseModel):
    item_description: str
    is_variant: bool = False
    direction: str | None = None


class RegenerateItemRequest(BaseModel):
    item_description: str | None = None


class GenerationJobResponse(BaseModel):
    id: uuid.UUID
    user_id: int
    name: str | None
    asset_type: AssetType
    directions: str
    camera_view: CameraView
    pixel_size: int
    global_description: str
    style_reference_url: str | None
    provider: str
    token_cost: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    items: list[GenerationItemResponse] = []

    model_config = {"from_attributes": True}

    @field_validator("style_reference_url", mode="before")
    @classmethod
    def _resolve(cls, v: str | None) -> str | None:
        return resolve_url(v) if v else v


class GenerationJobListResponse(BaseModel):
    id: uuid.UUID
    name: str | None
    asset_type: AssetType
    directions: str
    camera_view: CameraView
    pixel_size: int
    global_description: str
    provider: str
    status: JobStatus
    token_cost: int
    created_at: datetime
    preview_image_url: str | None = None
    items: list[GenerationItemResponse] = []

    model_config = {"from_attributes": True}
