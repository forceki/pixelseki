from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator

from app.core.storage import resolve_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.features.gallery.services import get_gallery_count, get_gallery_items

router = APIRouter(prefix="/gallery", tags=["Gallery"])


class GalleryItem(BaseModel):
    id: str
    source: str
    description: str
    output_image_url: str
    width: int | None
    height: int | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("output_image_url", mode="before")
    @classmethod
    def _resolve(cls, v: str | None) -> str | None:
        return resolve_url(v) if v else v


class GalleryResponse(BaseModel):
    items: list[GalleryItem]
    total: int
    has_more: bool


@router.get("", response_model=GalleryResponse)
async def list_gallery(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Lists all completed images for the authenticated user."""
    user_id = int(current_user["sub"])
    total = await get_gallery_count(session, user_id)
    rows = await get_gallery_items(session, user_id, limit=limit, offset=offset)

    return GalleryResponse(
        items=[GalleryItem(**row) for row in rows],
        total=total,
        has_more=(offset + limit) < total,
    )
