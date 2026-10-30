import logging
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image
from rembg import remove
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.image_provider import generate_image
from app.core.storage import save_file, read_file
from app.features.creations.models import Creation, CreationStatus
from app.features.creations.schemas import CreationCreate

logger = logging.getLogger(__name__)



def _remove_background(image_bytes: bytes) -> bytes:
    input_image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    output_image = remove(input_image)
    buf = BytesIO()
    output_image.save(buf, format="PNG")
    return buf.getvalue()


CREATION_DIRECTION_PROMPTS: dict[str, str] = {
    # Character
    "south": "Perspective: front-facing view (looking toward the viewer)",
    "south-east": "Perspective: 3/4 view from front-right angle",
    "east": "Perspective: right side profile view",
    "north": "Perspective: back view (facing away from the viewer)",
    # Background
    "horizontal-parallax": "Layout: horizontal parallax scrolling layer, seamless left-right edges",
    "isometric-skybox": "Perspective: isometric skybox background, wide atmospheric scene",
    # Place
    "top-down-map": "Perspective: top-down overhead map view, looking straight down like a 2D game map, bird's eye view",
    "exterior-cutout": "View: building exterior structure, architectural cutout style",
    "interior-cross-section": "View: interior cross-section, showing rooms and layout inside",
    "isometric-place": "Perspective: isometric 2.5D view of the place, angled 45-degree overhead like classic strategy games",
    # Environment
    "seamless-tile": "Layout: seamless tileable pattern, edges must loop perfectly in all directions",
    "standalone-prop": "Layout: standalone isolated prop/object, centered on canvas",
    # Item
    "flat-icon": "View: flat UI icon style, clean and centered, suitable for game inventory",
    "angled-display": "View: angled showcase display, slight 3/4 rotation for depth",
    # Other
    "none": "",
}


def _build_prompt(creation: Creation) -> str:
    direction_text = CREATION_DIRECTION_PROMPTS.get(creation.direction, "")
    if direction_text:
        direction_text = f"- {direction_text}\n"

    if creation.transparent_bg and creation.provider == "openai":
        bg_text = "- Background: transparent (no background)\n"
    elif creation.transparent_bg:
        bg_text = "- Background: solid pure black (#000000), flat, no gradients, no patterns\n"
    else:
        bg_text = "- Background: include an appropriate background that fits the scene\n"

    category_hint = ""
    if creation.category != "other":
        category_hint = f"- Category: {creation.category} asset for a 2D pixel art game\n"

    reference_text = ""
    if creation.reference_image_url:
        reference_text = (
            "REFERENCE: Match the art style, color palette, and level of detail "
            "from the attached reference image.\n\n"
        )

    return (
        f"Generate pixel art of: {creation.description}.\n\n"
        f"{reference_text}"
        f"Specifications:\n"
        f"- Style: 2D pixel art, clean edges, limited color palette\n"
        f"- Canvas size: {creation.width}x{creation.height} pixels\n"
        f"{category_hint}"
        f"{direction_text}"
        f"{bg_text}"
        f"- The artwork must be centered on the canvas\n"
        f"\nIMPORTANT: Output ONLY the pixel art image. "
        f"No text, no labels, no watermarks, no UI elements."
    )


async def create_creation(
    session: AsyncSession,
    *,
    user_id: int,
    data: CreationCreate,
    reference_image: bytes | None = None,
) -> Creation:
    creation = Creation(
        user_id=user_id,
        description=data.description,
        category=data.category,
        direction=data.direction,
        width=data.width,
        height=data.height,
        transparent_bg=data.transparent_bg,
        provider=data.provider,
    )
    session.add(creation)
    await session.flush()  # generates creation.id

    # Save reference image if provided
    if reference_image:
        creation.reference_image_url = save_file(
            f"creations/{creation.id}/reference.png", reference_image
        )

    await session.commit()
    await session.refresh(creation)
    return creation


async def run_creation(session: AsyncSession, creation: Creation) -> Creation:
    """Run the Gemini generation pipeline for a creation."""
    creation.status = CreationStatus.processing
    await session.commit()

    try:
        prompt = _build_prompt(creation)
        logger.info("Generating creation %s: %s", creation.id, prompt[:100])

        # Load reference image if available
        reference_image: bytes | None = None
        if creation.reference_image_url:
            reference_image = read_file(creation.reference_image_url)
            if reference_image:
                logger.info("Loaded reference image for creation %s (%d bytes)", creation.id, len(reference_image))
            else:
                logger.warning("Reference image not found: %s", creation.reference_image_url)
        else:
            logger.info("No reference image for creation %s", creation.id)

        image_bytes = await generate_image(
            prompt, session=session, provider=creation.provider,
            reference_image=reference_image, transparent_bg=creation.transparent_bg,
            user_id=creation.user_id,
        )

        # Save original
        creation.original_image_url = save_file(
            f"creations/{creation.id}/original.png", image_bytes
        )

        # Remove background if requested (skip for OpenAI — it handles transparency natively)
        if creation.transparent_bg and creation.provider != "openai":
            logger.info("Removing background for creation %s", creation.id)
            clean_bytes = _remove_background(image_bytes)
        else:
            clean_bytes = image_bytes

        creation.output_image_url = save_file(
            f"creations/{creation.id}/output.png", clean_bytes
        )
        creation.status = CreationStatus.completed
        await session.commit()
        await session.refresh(creation)
        logger.info("Creation %s completed", creation.id)

    except Exception as e:
        logger.error("Creation %s failed: %s", creation.id, e)
        creation.status = CreationStatus.failed
        await session.commit()
        await session.refresh(creation)

    return creation


async def get_creations_by_user(
    session: AsyncSession,
    user_id: int,
) -> list[Creation]:
    result = await session.execute(
        select(Creation)
        .where(Creation.user_id == user_id)
        .order_by(Creation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_creation_by_id(
    session: AsyncSession,
    creation_id: uuid.UUID,
) -> Creation | None:
    result = await session.execute(
        select(Creation).where(Creation.id == creation_id)
    )
    return result.scalar_one_or_none()


def _find_root_id(creation: Creation) -> uuid.UUID:
    """Get the root creation id (the original, version 0)."""
    return creation.parent_id if creation.parent_id else creation.id


async def get_versions(
    session: AsyncSession,
    creation: Creation,
) -> list[Creation]:
    """Get all versions of a creation (same root lineage)."""
    root_id = _find_root_id(creation)
    result = await session.execute(
        select(Creation)
        .where(
            (Creation.id == root_id) | (Creation.parent_id == root_id)
        )
        .order_by(Creation.version.asc())
    )
    return list(result.scalars().all())


async def delete_creation(
    session: AsyncSession,
    creation: Creation,
) -> None:
    await session.delete(creation)
    await session.commit()
