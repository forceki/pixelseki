import logging
import uuid
from io import BytesIO
from PIL import Image
from rembg import remove
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import humanize_error
from app.core.gemini import (
    CAMERA_LABELS,
    build_object_prompt,
    build_tileset_prompt,
    get_direction_labels,
)
from app.core.image_provider import generate_image
from app.core.storage import save_file, read_file, file_exists
from app.features.generations.models import (
    AssetType,
    GenerationItem,
    GenerationJob,
    JobStatus,
)
from app.features.generations.schemas import GenerationJobCreate

logger = logging.getLogger(__name__)



def remove_background(image_bytes: bytes) -> bytes:
    """Remove background from image using rembg and return transparent PNG."""
    input_image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    output_image = remove(input_image)
    buf = BytesIO()
    output_image.save(buf, format="PNG")
    return buf.getvalue()


async def create_generation_job(
    session: AsyncSession,
    *,
    user_id: int,
    data: GenerationJobCreate,
) -> GenerationJob:
    job = GenerationJob(
        user_id=user_id,
        asset_type=data.asset_type,
        directions=data.directions,
        camera_view=data.camera_view,
        pixel_size=data.pixel_size,
        global_description=data.global_description,
        style_reference_url=data.style_reference_url,
        provider=data.provider,
    )
    session.add(job)
    await session.flush()

    if data.asset_type == AssetType.object:
        # Create one item per direction
        labels = get_direction_labels(data.directions)
        for idx, label in enumerate(labels, start=1):
            item = GenerationItem(
                job_id=job.id,
                item_index=idx,
                item_description=f"{data.global_description} — facing {label}",
                direction=label,
            )
            session.add(item)
    else:
        # Tileset: use the items from the request
        for item_data in data.items:
            item = GenerationItem(
                job_id=job.id,
                item_index=item_data.item_index,
                item_description=item_data.item_description,
            )
            session.add(item)

    await session.commit()
    await session.refresh(job, attribute_names=["items"])
    return job


async def run_generation(session: AsyncSession, job: GenerationJob) -> GenerationJob:
    """Run Gemini image generation — one call per item."""
    job.status = JobStatus.processing
    await session.commit()

    camera = CAMERA_LABELS.get(job.camera_view, "side view")

    # Load reference image if one was uploaded
    reference_image: bytes | None = None
    if job.style_reference_url:
        reference_image = read_file(job.style_reference_url)
        if reference_image:
            logger.info("Job %s — using uploaded reference", job.id)

    has_ref = reference_image is not None

    try:
        if job.asset_type == AssetType.object:
            direction_labels = get_direction_labels(job.directions)

            # Sort items so "front" (item_index=1) is generated first
            sorted_items = sorted(job.items, key=lambda i: i.item_index)
            front_image: bytes | None = None

            for item in sorted_items:
                # Use stored direction if available, otherwise infer from index
                label = item.direction if item.direction else (
                    direction_labels[item.item_index - 1] if item.item_index <= len(direction_labels) else "front"
                )

                # Determine reference source
                if front_image is not None:
                    current_ref = front_image
                    ref_source = "generated"
                elif reference_image is not None:
                    current_ref = reference_image
                    ref_source = "uploaded"
                else:
                    current_ref = None
                    ref_source = "none"

                item.status = "processing"
                await session.commit()

                try:
                    prompt = build_object_prompt(
                        description=job.global_description,
                        direction=label,
                        camera=camera,
                        size=job.pixel_size,
                        reference_source=ref_source,
                        provider=job.provider,
                    )
                    logger.info("Job %s — generating direction '%s' (item %s, ref=%s)", job.id, label, item.item_index, ref_source)

                    image_bytes = await generate_image(prompt, session=session, provider=job.provider, job_id=job.id, item_index=item.item_index, reference_image=current_ref, transparent_bg=True, user_id=job.user_id)

                    # Save original
                    original_filename = f"dir_{item.item_index}_{label}_original.png"
                    item.original_image_url = save_file(f"generations/{job.id}/{original_filename}", image_bytes)

                    # Remove background (skip for OpenAI — it handles transparency natively)
                    if job.provider == "openai":
                        clean_bytes = image_bytes
                    else:
                        logger.info("Job %s — removing background for item %s", job.id, item.item_index)
                        clean_bytes = remove_background(image_bytes)
                    clean_filename = f"dir_{item.item_index}_{label}.png"
                    item.output_image_url = save_file(f"generations/{job.id}/{clean_filename}", clean_bytes)

                    item.status = "completed"
                    await session.commit()

                    # After first direction, capture it as reference for the rest
                    if front_image is None:
                        front_image = image_bytes
                        logger.info("Job %s — front direction generated, using as reference for remaining directions", job.id)

                except Exception as item_err:
                    logger.error("Job %s — item %s failed: %s", job.id, item.item_index, item_err)
                    item.status = "failed"
                    item.error_message = humanize_error(item_err)
                    await session.commit()

        else:
            # Tileset: generate first tile, then use it as reference for the rest
            sorted_items = sorted(job.items, key=lambda i: i.item_index)
            first_tile: bytes | None = None

            for item in sorted_items:
                current_ref = reference_image if first_tile is None else first_tile

                item.status = "processing"
                await session.commit()

                try:
                    prompt = build_tileset_prompt(
                        global_description=job.global_description,
                        item_description=item.item_description,
                        camera=camera,
                        size=job.pixel_size,
                        has_reference=current_ref is not None,
                        provider=job.provider,
                    )
                    logger.info("Job %s — generating tile '%s' (item %s, ref=%s)", job.id, item.item_description[:40], item.item_index, current_ref is not None)

                    image_bytes = await generate_image(prompt, session=session, provider=job.provider, job_id=job.id, item_index=item.item_index, reference_image=current_ref, transparent_bg=True, user_id=job.user_id)

                    # Save original
                    original_filename = f"tile_{item.item_index}_original.png"
                    item.original_image_url = save_file(f"generations/{job.id}/{original_filename}", image_bytes)

                    # Remove background (skip for OpenAI — it handles transparency natively)
                    if job.provider == "openai":
                        clean_bytes = image_bytes
                    else:
                        logger.info("Job %s — removing background for tile %s", job.id, item.item_index)
                        clean_bytes = remove_background(image_bytes)
                    clean_filename = f"tile_{item.item_index}.png"
                    item.output_image_url = save_file(f"generations/{job.id}/{clean_filename}", clean_bytes)

                    item.status = "completed"
                    await session.commit()

                    # Capture first tile as reference for remaining tiles
                    if first_tile is None:
                        first_tile = image_bytes
                        logger.info("Job %s — first tile generated, using as reference for remaining tiles", job.id)

                except Exception as item_err:
                    logger.error("Job %s — tile %s failed: %s", job.id, item.item_index, item_err)
                    item.status = "failed"
                    item.error_message = humanize_error(item_err)
                    await session.commit()

        # Check if any items failed
        any_failed = any(i.status == "failed" for i in job.items)
        if any_failed:
            job.status = JobStatus.failed
            logger.warning("Job %s finished with %d failed items", job.id, sum(1 for i in job.items if i.status == "failed"))
        else:
            job.status = JobStatus.completed
            logger.info("Job %s completed — %d images generated", job.id, len(job.items))

        await session.commit()
        await session.refresh(job, attribute_names=["items"])

    except Exception as e:
        logger.error("Job %s failed: %s", job.id, e)
        error_msg = humanize_error(e)
        # Mark all remaining pending/processing items as failed
        for item in job.items:
            if item.status in ("pending", "processing"):
                item.status = "failed"
                item.error_message = error_msg
        job.status = JobStatus.failed
        await session.commit()
        await session.refresh(job)

    return job


async def get_item_by_id(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> GenerationItem | None:
    result = await session.execute(
        select(GenerationItem).where(GenerationItem.id == item_id)
    )
    return result.scalar_one_or_none()


MAX_EDITS = 2
MAX_REDOS = 2


def _get_reference_image(job: GenerationJob) -> bytes | None:
    """Load the first completed original image as reference."""
    for item in job.items:
        if item.original_image_url:
            data = read_file(item.original_image_url)
            if data:
                logger.info("Using reference image from item %s", item.item_index)
                return data
    return None


async def regenerate_item(
    session: AsyncSession,
    job: GenerationJob,
    new_item: GenerationItem,
) -> GenerationItem:
    """Generate image for a new versioned item, using existing images as reference."""
    camera = CAMERA_LABELS.get(job.camera_view, "side view")

    # Load reference image from existing items for style consistency
    reference_image = _get_reference_image(job)
    ref_source = "generated" if reference_image else "none"

    version_suffix = f"_v{new_item.version}" if new_item.version > 0 else ""

    if job.asset_type == AssetType.object:
        # Determine if this is a variant or a direction
        is_variant = new_item.tag == "variant"

        if is_variant:
            label = "variant"
            item_ref_source = "variant" if reference_image else "none"
        elif new_item.direction:
            # Use the explicitly stored direction
            label = new_item.direction
            item_ref_source = ref_source
        else:
            # Fallback: infer from item_index (for original job items)
            direction_labels = get_direction_labels(job.directions)
            label = direction_labels[new_item.item_index - 1] if new_item.item_index <= len(direction_labels) else "front"
            item_ref_source = ref_source

        prompt = build_object_prompt(
            description=new_item.item_description,
            direction=label,
            camera=camera,
            size=job.pixel_size,
            reference_source=item_ref_source,
            provider=job.provider,
        )
        original_filename = f"dir_{new_item.item_index}_{label}{version_suffix}_original.png"
        clean_filename = f"dir_{new_item.item_index}_{label}{version_suffix}.png"
    else:
        prompt = build_tileset_prompt(
            global_description=job.global_description,
            item_description=new_item.item_description,
            camera=camera,
            size=job.pixel_size,
            has_reference=reference_image is not None,
            provider=job.provider,
        )
        original_filename = f"tile_{new_item.item_index}{version_suffix}_original.png"
        clean_filename = f"tile_{new_item.item_index}{version_suffix}.png"

    new_item.status = "processing"
    await session.commit()

    try:
        logger.info("Generating item %s (v%d) for job %s (ref=%s)", new_item.id, new_item.version, job.id, ref_source)
        image_bytes = await generate_image(
            prompt,
            session=session,
            provider=job.provider,
            job_id=job.id,
            item_index=new_item.item_index,
            reference_image=reference_image,
            transparent_bg=True,
            user_id=job.user_id,
        )

        new_item.original_image_url = save_file(f"generations/{job.id}/{original_filename}", image_bytes)

        if job.provider == "openai":
            clean_bytes = image_bytes
        else:
            clean_bytes = remove_background(image_bytes)
        new_item.output_image_url = save_file(f"generations/{job.id}/{clean_filename}", clean_bytes)

        new_item.status = "completed"
        await session.commit()
        await session.refresh(new_item)
        logger.info("Item %s (v%d) generated successfully", new_item.id, new_item.version)

    except Exception as e:
        logger.error("Item %s (v%d) failed: %s", new_item.id, new_item.version, e)
        new_item.status = "failed"
        new_item.error_message = humanize_error(e)
        await session.commit()
        await session.refresh(new_item)

    return new_item


async def get_jobs_by_user(
    session: AsyncSession,
    user_id: int,
) -> list[GenerationJob]:
    result = await session.execute(
        select(GenerationJob)
        .options(selectinload(GenerationJob.items))
        .where(GenerationJob.user_id == user_id)
        .order_by(GenerationJob.created_at.desc())
    )
    return list(result.scalars().all())


async def get_job_by_id(
    session: AsyncSession,
    job_id: uuid.UUID,
) -> GenerationJob | None:
    result = await session.execute(
        select(GenerationJob)
        .options(selectinload(GenerationJob.items))
        .where(GenerationJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def update_job_status(
    session: AsyncSession,
    job: GenerationJob,
    status: JobStatus,
) -> GenerationJob:
    job.status = status
    await session.commit()
    await session.refresh(job)
    return job


async def update_job(
    session: AsyncSession,
    job: GenerationJob,
    **kwargs: object,
) -> GenerationJob:
    for key, value in kwargs.items():
        if hasattr(job, key) and value is not None:
            setattr(job, key, value)
    await session.commit()
    await session.refresh(job, attribute_names=["items"])
    return job


async def delete_job(
    session: AsyncSession,
    job: GenerationJob,
) -> None:
    await session.delete(job)
    await session.commit()


def create_animation_gif(job: GenerationJob, duration: int = 200) -> bytes:
    """Combine all completed item images into an animated GIF."""
    frames: list[Image.Image] = []

    sorted_items = sorted(job.items, key=lambda i: i.item_index)
    for item in sorted_items:
        if item.output_image_url:
            data = read_file(item.output_image_url)
            if data:
                img = Image.open(BytesIO(data)).convert("RGBA")
                frames.append(img)

    if not frames:
        raise ValueError("No completed images to animate")

    buf = BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
    )
    return buf.getvalue()


async def delete_item(
    session: AsyncSession,
    item: GenerationItem,
) -> None:
    await session.delete(item)
    await session.commit()
