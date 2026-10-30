import asyncio
import io
import json
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_session
from app.core.security import get_current_user
from app.core.upload import validate_image_upload
from app.features.generations.schemas import (
    AddItemRequest,
    GenerationItemResponse,
    GenerationJobCreate,
    GenerationJobListResponse,
    GenerationJobResponse,
    GenerationJobUpdate,
    RegenerateItemRequest,
)
from app.core.tasks import generate_pixel_art_task, regenerate_item_task
from app.features.generations.models import GenerationItem
from app.core.config import settings
from app.features.users.services import get_user_by_id
from app.core.storage import save_file, read_file
from app.features.generations.services import (
    MAX_EDITS,
    MAX_REDOS,
    create_animation_gif,
    create_generation_job,
    delete_item,
    delete_job,
    get_item_by_id,
    get_job_by_id,
    get_jobs_by_user,
    update_job,
)

router = APIRouter(prefix="/generations", tags=["Generations"])


@router.post("", response_model=GenerationJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    asset_type: str = Form(...),
    directions: str = Form(...),
    camera_view: str = Form(...),
    pixel_size: int = Form(...),
    global_description: str = Form(...),
    items_json: str = Form("[]"),
    provider: str = Form(None),
    reference_file: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new generation job with optional reference image."""
    import json as json_mod
    user_id = int(current_user["sub"])

    provider = provider or settings.DEFAULT_PROVIDER
    if provider not in ("gemini", "openai"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider. Use 'gemini' or 'openai'.")

    # Check generation credits
    user = await get_user_by_id(session, user_id)
    if not user or user.generation_credits < 1:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient generation credits")

    items_data = json_mod.loads(items_json)
    data = GenerationJobCreate(
        asset_type=asset_type,
        directions=directions,
        camera_view=camera_view,
        pixel_size=pixel_size,
        global_description=global_description,
        provider=provider,
        items=[{"item_index": i["item_index"], "item_description": i["item_description"]} for i in items_data],
    )

    # Calculate cost: 1 credit per item/direction
    from app.core.gemini import get_direction_labels
    from app.features.generations.models import AssetType as AT
    if data.asset_type == AT.object:
        cost = len(get_direction_labels(data.directions))
    else:
        cost = max(len(data.items), 1)

    if user.generation_credits < cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Not enough credits. Need {cost}, have {user.generation_credits}",
        )

    # Deduct credits upfront
    user.generation_credits -= cost
    await session.flush()

    image_data: bytes | None = None
    if reference_file:
        image_data = await validate_image_upload(reference_file)

    job = await create_generation_job(session, user_id=user_id, data=data)
    job.token_cost = cost

    # Save reference file if provided
    if image_data:
        job.style_reference_url = save_file(
            f"generations/{job.id}/reference.png", image_data
        )
        await session.commit()
        await session.refresh(job, attribute_names=["items"])

    await generate_pixel_art_task.kiq(str(job.id))
    return job


@router.get("", response_model=list[GenerationJobListResponse])
async def list_jobs(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all generation jobs for the current user."""
    user_id = int(current_user["sub"])
    return await get_jobs_by_user(session, user_id)


@router.get("/{job_id}", response_model=GenerationJobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a single generation job with its items."""
    job = await get_job_by_id(session, job_id)
    if not job or job.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{job_id}/download")
async def download_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Download all generated images as a zip file."""
    job = await get_job_by_id(session, job_id)
    if not job or job.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status.value != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job not completed")

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in job.items:
            if item.output_image_url:
                data = read_file(item.output_image_url)
                if data:
                    arcname = Path(item.output_image_url).name
                    zf.writestr(arcname, data)

            if item.original_image_url:
                data = read_file(item.original_image_url)
                if data:
                    arcname = Path(item.original_image_url).name
                    zf.writestr(f"originals/{arcname}", data)

    buf.seek(0)

    name = job.name or job.global_description[:30]
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.zip"'},
    )


@router.get("/{job_id}/stream")
async def stream_job_status(
    job_id: uuid.UUID,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """SSE stream that polls job status until completed or failed."""

    async def event_stream():
        while True:
            if await request.is_disconnected():
                break

            async with async_session_factory() as session:
                job = await get_job_by_id(session, job_id)

            if not job or job.user_id != int(current_user["sub"]):
                yield f"data: {json.dumps({'status': 'error', 'detail': 'Not found'})}\n\n"
                break

            payload = {
                "status": job.status.value,
                "items": [
                    {
                        "item_index": item.item_index,
                        "output_image_url": item.output_image_url,
                        "status": item.status,
                        "error_message": item.error_message,
                    }
                    for item in job.items
                ],
            }
            yield f"data: {json.dumps(payload)}\n\n"

            if job.status.value in ("completed", "failed"):
                break

            await asyncio.sleep(2)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{job_id}", response_model=GenerationJobResponse)
async def patch_job(
    job_id: uuid.UUID,
    body: GenerationJobUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update a generation job (name, etc.)."""
    job = await get_job_by_id(session, job_id)
    if not job or job.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job = await update_job(session, job, **body.model_dump(exclude_unset=True))
    return job


@router.post("/{job_id}/items", response_model=GenerationItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item(
    job_id: uuid.UUID,
    body: AddItemRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Add a new direction/tile item to an existing job and enqueue generation."""
    user_id = int(current_user["sub"])
    job = await get_job_by_id(session, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Check credits (1 per item)
    user = await get_user_by_id(session, user_id)
    if not user or user.generation_credits < 1:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient generation credits")
    user.generation_credits -= 1
    await session.flush()

    # Next item_index
    max_index = max((item.item_index for item in job.items), default=0)

    new_item = GenerationItem(
        job_id=job.id,
        item_index=max_index + 1,
        item_description=body.item_description,
        direction=body.direction,
        version=0,
        tag="variant" if body.is_variant else "original",
    )
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)

    await regenerate_item_task.kiq(str(job_id), str(new_item.id))

    return new_item


@router.post("/{job_id}/items/{item_id}/regenerate", response_model=GenerationItemResponse)
async def regenerate_item_endpoint(
    job_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RegenerateItemRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new versioned item and enqueue regeneration."""
    user_id = int(current_user["sub"])
    job = await get_job_by_id(session, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Check credits (1 per regeneration)
    user = await get_user_by_id(session, user_id)
    if not user or user.generation_credits < 1:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient generation credits")
    user.generation_credits -= 1
    await session.flush()

    source_item = await get_item_by_id(session, item_id)
    if not source_item or source_item.job_id != job_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    is_edit = body.item_description is not None and body.item_description != source_item.item_description

    if is_edit and source_item.edit_count >= MAX_EDITS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Edit limit reached ({MAX_EDITS} max)",
        )
    if not is_edit and source_item.redo_count >= MAX_REDOS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Redo limit reached ({MAX_REDOS} max)",
        )

    # Bump counters on the source item
    if is_edit:
        source_item.edit_count += 1
    else:
        source_item.redo_count += 1
    await session.flush()

    # Determine new version number
    new_version = source_item.version + 1
    new_tag = f"v{new_version}" if is_edit else f"v{new_version}"

    # Create a new item as a new version
    new_item = GenerationItem(
        job_id=job.id,
        item_index=source_item.item_index,
        item_description=body.item_description if is_edit else source_item.item_description,
        version=new_version,
        tag=new_tag,
        edit_count=0,
        redo_count=0,
    )
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)

    # Enqueue background generation
    await regenerate_item_task.kiq(str(job_id), str(new_item.id))

    return new_item


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a generation job."""
    job = await get_job_by_id(session, job_id)
    if not job or job.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    await delete_job(session, job)


@router.delete("/{job_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    job_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a single generation item."""
    job = await get_job_by_id(session, job_id)
    if not job or job.user_id != int(current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    item = await get_item_by_id(session, item_id)
    if not item or item.job_id != job.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    await delete_item(session, item)
