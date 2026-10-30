import io
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.core.upload import validate_image_upload
from app.core.tasks import run_creation_task
from app.features.creations.models import Creation as CreationModel, CreationCategory
from app.features.creations.schemas import CreationCreate, CreationResponse, RegenerateCreationRequest
from app.core.storage import read_file
from app.features.creations.services import (
    create_creation,
    delete_creation,
    get_creation_by_id,
    get_creations_by_user,
    get_versions,
)
from app.core.config import settings
from app.features.users.services import get_user_by_id

router = APIRouter(prefix="/creations", tags=["Creations"])


@router.post("", response_model=CreationResponse, status_code=status.HTTP_201_CREATED)
async def create(
    description: str = Form(...),
    category: CreationCategory = Form(CreationCategory.other),
    direction: str = Form("none"),
    width: int = Form(64),
    height: int = Form(64),
    transparent_bg: bool = Form(False),
    provider: str = Form(None),
    reference_image: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new creation and enqueue background generation."""
    user_id = int(current_user["sub"])

    provider = provider or settings.DEFAULT_PROVIDER
    if provider not in ("gemini", "openai"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider. Use 'gemini' or 'openai'.")

    # Check generation credits (1 per creation)
    user = await get_user_by_id(session, user_id)
    if not user or user.generation_credits < 1:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient generation credits")
    user.generation_credits -= 1
    await session.flush()

    data = CreationCreate(
        description=description,
        category=category,
        direction=direction,
        width=width,
        height=height,
        transparent_bg=transparent_bg,
        provider=provider,
    )

    # Validate and read reference image if provided
    reference_image_bytes: bytes | None = None
    if reference_image and reference_image.filename:
        reference_image_bytes = await validate_image_upload(reference_image)

    creation = await create_creation(
        session, user_id=user_id, data=data, reference_image=reference_image_bytes
    )
    await run_creation_task.kiq(str(creation.id))
    return creation


@router.get("", response_model=list[CreationResponse])
async def list_creations(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all creations for the current user."""
    user_id = int(current_user["sub"])
    return await get_creations_by_user(session, user_id)


@router.get("/{creation_id}", response_model=CreationResponse)
async def get_creation(
    creation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a single creation."""
    creation = await get_creation_by_id(session, creation_id)
    if not creation or creation.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creation not found")
    return creation


@router.get("/{creation_id}/download")
async def download_creation(
    creation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Download creation images as a zip."""
    creation = await get_creation_by_id(session, creation_id)
    if not creation or creation.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creation not found")

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if creation.output_image_url:
            data = read_file(creation.output_image_url)
            if data:
                zf.writestr(Path(creation.output_image_url).name, data)
        if creation.original_image_url:
            data = read_file(creation.original_image_url)
            if data:
                zf.writestr(f"originals/{Path(creation.original_image_url).name}", data)

    buf.seek(0)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in creation.description[:30]).strip()

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.zip"'},
    )


@router.get("/{creation_id}/versions", response_model=list[CreationResponse])
async def list_versions(
    creation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get all versions of a creation."""
    creation = await get_creation_by_id(session, creation_id)
    if not creation or creation.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creation not found")
    return await get_versions(session, creation)


@router.post("/{creation_id}/regenerate", response_model=CreationResponse, status_code=status.HTTP_201_CREATED)
async def regenerate_creation(
    creation_id: uuid.UUID,
    body: RegenerateCreationRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new version of a creation and enqueue generation."""
    user_id = int(current_user["sub"])
    source = await get_creation_by_id(session, creation_id)
    if not source or source.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creation not found")

    # Check generation credits (1 per regeneration)
    user = await get_user_by_id(session, user_id)
    if not user or user.generation_credits < 1:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient generation credits")
    user.generation_credits -= 1
    await session.flush()

    root_id = source.parent_id if source.parent_id else source.id

    new_creation = CreationModel(
        user_id=source.user_id,
        description=body.description if body.description else source.description,
        category=source.category,
        direction=source.direction,
        width=source.width,
        height=source.height,
        transparent_bg=source.transparent_bg,
        provider=source.provider,
        version=source.version + 1,
        parent_id=root_id,
    )
    session.add(new_creation)
    await session.commit()
    await session.refresh(new_creation)

    await run_creation_task.kiq(str(new_creation.id))
    return new_creation


@router.delete("/{creation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_creation(
    creation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a creation."""
    creation = await get_creation_by_id(session, creation_id)
    if not creation or creation.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creation not found")
    await delete_creation(session, creation)
