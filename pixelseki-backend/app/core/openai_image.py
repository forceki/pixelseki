import base64
import logging
import time
import uuid

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

MODEL = "gpt-image-1.5"

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_image_openai(
    prompt: str,
    session: AsyncSession,
    job_id: uuid.UUID | None = None,
    item_index: int | None = None,
    reference_image: bytes | None = None,
    size: str = "1024x1024",
    quality: str = "high",
    transparent_bg: bool = False,
    user_id: int | None = None,
) -> bytes:
    """Call OpenAI to generate an image, log the result to DB, return image bytes."""
    from app.features.generations.log_model import GeminiLog

    start = time.time()
    response_text = None
    image_bytes = None
    error_type = None
    error_detail = None
    log_status = "success"
    input_tokens = None
    output_tokens = None
    total_tokens = None

    try:
        background = "transparent" if transparent_bg else "opaque"

        if reference_image:
            # Use images.edit for reference-based generation
            import io
            ref_file = io.BytesIO(reference_image)
            ref_file.name = "reference.png"

            response = await client.images.edit(
                model=MODEL,
                image=ref_file,
                prompt=prompt,
                n=1,
                size=size,
                background=background,
            )
        else:
            # Text-to-image generation
            response = await client.images.generate(
                model=MODEL,
                prompt=prompt,
                n=1,
                size=size,
                quality=quality,
                background=background,
            )

        # Extract token usage from response
        if response.usage:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = response.usage.total_tokens

        image_data = response.data[0]

        if image_data.b64_json:
            image_bytes = base64.b64decode(image_data.b64_json)
        elif image_data.url:
            # Download from URL if b64 not available
            import httpx
            async with httpx.AsyncClient() as http:
                resp = await http.get(image_data.url)
                resp.raise_for_status()
                image_bytes = resp.content

        if image_data.revised_prompt:
            response_text = image_data.revised_prompt

    except Exception as e:
        log_status = "error"
        error_type = type(e).__name__
        error_detail = str(e)
        raise
    finally:
        duration_ms = int((time.time() - start) * 1000)

        log = GeminiLog(
            user_id=user_id,
            job_id=job_id,
            item_index=item_index,
            model=MODEL,
            prompt=prompt,
            status=log_status,
            duration_ms=duration_ms,
            image_size_bytes=len(image_bytes) if image_bytes else None,
            image_mime_type="image/png" if image_bytes else None,
            response_text=response_text,
            error_type=error_type,
            error_detail=error_detail,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        session.add(log)

        # Accumulate per-user token totals
        if user_id and input_tokens is not None:
            from app.features.users.models import User
            user = await session.get(User, user_id)
            if user:
                user.total_input_tokens += input_tokens or 0
                user.total_output_tokens += output_tokens or 0

        await session.commit()

    if image_bytes is None:
        raise ValueError("OpenAI returned no image data")

    return image_bytes
