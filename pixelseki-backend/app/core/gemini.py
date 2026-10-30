import logging
import time
import uuid

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.features.generations.models import CameraView

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash-image"

client = genai.Client(api_key=settings.GEMINI_API_KEY)

CAMERA_LABELS = {
    CameraView.side_view: "side view",
    CameraView.top_down: "top-down view",
    CameraView.isometric: "isometric 2.5D view",
}

# ── Direction System (Cartesian 2D, Y-Down game engine layout) ──

DIRECTION_LABELS_4 = ["south", "east", "west", "north"]
DIRECTION_LABELS_8 = [
    "south",
    "south_east",
    "east",
    "north_east",
    "north",
    "north_west",
    "west",
    "south_west",
]


def get_direction_labels(directions: str) -> list[str]:
    """Return the list of direction labels based on the directions config."""
    if directions == "8 Directions":
        return DIRECTION_LABELS_8
    elif directions == "4 Directions":
        return DIRECTION_LABELS_4
    else:
        return ["south"]


DIRECTION_SPECS = {
    # 4-way orthogonal directions
    "south": {
        "label": "Front View",
        "degrees": 180,
        "prompt": (
            "Direction: SOUTH — Front View (180°). "
            "The character/object faces directly toward the viewer. "
            "100% front surface visible, 0% side. "
            "This is the default forward-facing sprite."
        ),
    },
    "east": {
        "label": "Right Profile View",
        "degrees": 90,
        "prompt": (
            "Direction: EAST — Right Profile View (90°). "
            "The character/object is rotated 90° clockwise so the RIGHT SIDE faces the viewer. "
            "0% front visible, 100% right side profile. "
            "Show a pure side silhouette from the right."
        ),
    },
    "west": {
        "label": "Left Profile View",
        "degrees": 270,
        "prompt": (
            "Direction: WEST — Left Profile View (270°). "
            "The character/object is rotated 90° counter-clockwise so the LEFT SIDE faces the viewer. "
            "0% front visible, 100% left side profile. "
            "This is the horizontal mirror of the EAST view."
        ),
    },
    "north": {
        "label": "Back View",
        "degrees": 0,
        "prompt": (
            "Direction: NORTH — Back View (0°). "
            "The character/object faces AWAY from the viewer. "
            "100% back surface visible. "
            "Show the rear/backside — the opposite of the SOUTH/front view."
        ),
    },
    # 8-way diagonal directions
    "south_east": {
        "label": "3/4 Front-Right View",
        "degrees": 135,
        "prompt": (
            "Direction: SOUTH-EAST — 3/4 Front-Right View (135°). "
            "The character/object is angled between front and right side. "
            "50% front visible, 50% right side visible. "
            "Classic RPG 3/4 perspective showing front-right diagonal."
        ),
    },
    "north_east": {
        "label": "3/4 Back-Right View",
        "degrees": 45,
        "prompt": (
            "Direction: NORTH-EAST — 3/4 Back-Right View (45°). "
            "The character/object shows back-right diagonal angle. "
            "30% back visible, 70% right side visible. "
            "The viewer sees mostly the right side with some of the back."
        ),
    },
    "north_west": {
        "label": "3/4 Back-Left View",
        "degrees": 315,
        "prompt": (
            "Direction: NORTH-WEST — 3/4 Back-Left View (315°). "
            "The character/object shows back-left diagonal angle. "
            "30% back visible, 70% left side visible. "
            "Mirror of the NORTH-EAST view."
        ),
    },
    "south_west": {
        "label": "3/4 Front-Left View",
        "degrees": 225,
        "prompt": (
            "Direction: SOUTH-WEST — 3/4 Front-Left View (225°). "
            "The character/object is angled between front and left side. "
            "50% front visible, 50% left side visible. "
            "Mirror of the SOUTH-EAST view."
        ),
    },
    # Extra directions
    "top": {
        "label": "Top-Down View",
        "degrees": -1,
        "prompt": (
            "Direction: TOP — Bird's Eye View. "
            "The viewer looks straight down from above. "
            "Show the top of the character/object."
        ),
    },
    "bottom": {
        "label": "Bottom View",
        "degrees": -1,
        "prompt": (
            "Direction: BOTTOM — Worm's Eye View. "
            "The viewer looks straight up from below. "
            "Show the underside of the character/object."
        ),
    },
}


def _bg_instruction(provider: str) -> str:
    """Return the background instruction based on the provider."""
    if provider == "openai":
        return "Background: transparent (no background)"
    return "Background: solid pure black (#000000)"


def build_object_prompt(
    description: str,
    direction: str,
    camera: str,
    size: int,
    reference_source: str = "none",
    provider: str = "gemini",
) -> str:
    """Build a prompt for a single direction of an object sprite.

    reference_source:
      - "none": no reference image, full description needed
      - "uploaded": user uploaded a style reference from FE
      - "generated": front-facing result used as reference for other directions
      - "variant": same object with modifications, uses existing sprite as style reference
    """

    spec = DIRECTION_SPECS.get(direction)
    dir_prompt = spec["prompt"] if spec else f"Direction: {direction}."
    dir_label = spec["label"] if spec else direction
    dir_degrees = spec["degrees"] if spec else -1

    bg = _bg_instruction(provider)

    if reference_source == "variant":
        return (
            f"The attached image is an existing pixel art sprite. "
            f"Generate a VARIANT of this sprite: {description}.\n\n"
            f"Keep the same art style, proportions, pixel detail, and level of quality. "
            f"Apply the requested changes while maintaining visual consistency with the original.\n\n"
            f"Specifications:\n"
            f"- Style: 2D pixel art, clean edges, limited color palette\n"
            f"- Canvas size: {size}x{size} pixels\n"
            f"- Camera angle: {camera}\n"
            f"- {bg}\n"
            f"- Single sprite only, one frame\n"
            f"\nOutput ONLY the pixel art image. No text, no labels."
        )

    if reference_source == "generated":
        # Gemini can SEE the south/front — keep it short, specify exact rotation
        rotation_note = ""
        if dir_degrees >= 0:
            south_deg = 180
            rotation = (dir_degrees - south_deg) % 360
            rotation_note = f"Rotate the character {rotation}° from the front-facing (south) position. "

        return (
            f"The attached image is the SOUTH (front-facing, 180°) view of this pixel art character/object. "
            f"Generate the SAME character/object showing the {dir_label} ({direction}) angle.\n\n"
            f"{rotation_note}"
            f"{dir_prompt}\n\n"
            f"- Canvas size: {size}x{size} pixels\n"
            f"- Keep identical art style, colors, proportions, and pixel detail\n"
            f"- {bg}\n"
            f"\nOutput ONLY the pixel art image. No text, no labels."
        )

    if reference_source == "uploaded":
        return (
            f"Generate a pixel art sprite of: {description}.\n\n"
            f"STYLE REFERENCE: Match the art style, color palette, and level of detail "
            f"from the attached reference image.\n\n"
            f"{dir_prompt}\n\n"
            f"Specifications:\n"
            f"- Style: 2D pixel art, clean edges, limited color palette\n"
            f"- Canvas size: {size}x{size} pixels\n"
            f"- Camera angle: {camera}\n"
            f"- {bg}\n"
            f"- Single sprite only, one frame\n"
            f"\nOutput ONLY the pixel art image. No text, no labels."
        )

    # No reference — full description
    return (
        f"Generate a pixel art sprite of: {description}.\n\n"
        f"{dir_prompt}\n\n"
        f"Specifications:\n"
        f"- Style: 2D pixel art, clean edges, limited color palette\n"
        f"- Canvas size: {size}x{size} pixels\n"
        f"- Camera angle: {camera}\n"
        f"- {bg}, flat, no gradients, no patterns\n"
        f"- The sprite must be centered on the canvas with consistent padding\n"
        f"- Single sprite only, one frame, one direction\n"
        f"\nIMPORTANT: Output ONLY the pixel art image. "
        f"No text, no labels, no watermarks, no UI elements."
    )


def build_tileset_prompt(
    global_description: str,
    item_description: str,
    camera: str,
    size: int,
    has_reference: bool = False,
    provider: str = "gemini",
) -> str:
    """Build a prompt for a single tile in a tileset."""
    bg = _bg_instruction(provider)

    ref_note = ""
    if has_reference:
        ref_note = (
            "\nREFERENCE IMAGE: I have attached a reference image from this tileset. "
            "You MUST match the exact same art style, color palette, and level of detail. "
            "Generate a new tile that visually belongs in the same set.\n"
        )

    return (
        f"Generate a single pixel art tile for a tileset themed: {global_description}.\n\n"
        f"This specific tile is: {item_description}.\n"
        f"{ref_note}\n"
        f"Specifications:\n"
        f"- Style: 2D pixel art, clean edges, limited color palette\n"
        f"- Canvas size: {size}x{size} pixels\n"
        f"- Camera angle: {camera}\n"
        f"- {bg}, flat, no gradients, no patterns\n"
        f"- Single tile only, centered on canvas\n"
        f"\nIMPORTANT: Output ONLY the pixel art image. "
        f"No text, no labels, no watermarks, no UI elements."
    )


async def generate_image(
    prompt: str,
    session: AsyncSession,
    job_id: uuid.UUID | None = None,
    item_index: int | None = None,
    reference_image: bytes | None = None,
    user_id: int | None = None,
) -> bytes:
    """Call Gemini to generate an image, log the result to DB, return image bytes."""
    from app.features.generations.log_model import GeminiLog

    # Build multimodal contents if reference image provided
    if reference_image:
        contents = [
            types.Part.from_bytes(data=reference_image, mime_type="image/png"),
            prompt,
        ]
    else:
        contents = prompt

    start = time.time()
    response_text = None
    image_bytes = None
    image_mime = None
    error_type = None
    error_detail = None
    status = "success"
    input_tokens = None
    output_tokens = None
    total_tokens = None

    try:
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract token usage from response
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
            total_tokens = response.usage_metadata.total_token_count

        for part in response.candidates[0].content.parts:
            if part.text:
                response_text = part.text
            if part.inline_data is not None and image_bytes is None:
                image_bytes = part.inline_data.data
                image_mime = part.inline_data.mime_type

    except Exception as e:
        status = "error"
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
            status=status,
            duration_ms=duration_ms,
            image_size_bytes=len(image_bytes) if image_bytes else None,
            image_mime_type=image_mime,
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
        raise ValueError("Gemini returned no image data")

    return image_bytes
