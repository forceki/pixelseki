"""Unified image generation dispatcher — routes to Gemini or OpenAI."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gemini import generate_image as generate_image_gemini
from app.core.openai_image import generate_image_openai


async def generate_image(
    prompt: str,
    session: AsyncSession,
    provider: str = "gemini",
    job_id: uuid.UUID | None = None,
    item_index: int | None = None,
    reference_image: bytes | None = None,
    transparent_bg: bool = False,
    user_id: int | None = None,
) -> bytes:
    """Generate an image using the specified provider.

    Args:
        provider: "gemini" or "openai"
        transparent_bg: If True, OpenAI generates with transparent background natively.
                        For Gemini, background removal is handled separately by rembg.
        user_id: Owner of the request — used for per-log and per-user token tracking.
    """
    if provider == "openai":
        return await generate_image_openai(
            prompt=prompt,
            session=session,
            job_id=job_id,
            item_index=item_index,
            reference_image=reference_image,
            transparent_bg=transparent_bg,
            user_id=user_id,
        )

    # Default to Gemini
    return await generate_image_gemini(
        prompt=prompt,
        session=session,
        job_id=job_id,
        item_index=item_index,
        reference_image=reference_image,
        user_id=user_id,
    )
