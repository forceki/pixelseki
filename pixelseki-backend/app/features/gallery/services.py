from sqlalchemy import String, cast, desc, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.creations.models import Creation, CreationStatus
from app.features.generations.models import GenerationItem, GenerationJob, JobStatus


def _build_combined_query(user_id: int):
    """Build the UNION ALL query combining creations and generation items for a specific user."""

    creations_q = (
        select(
            cast(Creation.id, String).label("id"),
            literal("creation").label("source"),
            Creation.description.label("description"),
            Creation.output_image_url.label("output_image_url"),
            Creation.width.label("width"),
            Creation.height.label("height"),
            Creation.created_at.label("created_at"),
        )
        .where(
            Creation.user_id == user_id,
            Creation.status == CreationStatus.completed,
            Creation.output_image_url.isnot(None),
            Creation.parent_id.is_(None),
        )
    )

    gen_items_q = (
        select(
            cast(GenerationItem.id, String).label("id"),
            literal("generation").label("source"),
            GenerationItem.item_description.label("description"),
            GenerationItem.output_image_url.label("output_image_url"),
            GenerationJob.pixel_size.label("width"),
            GenerationJob.pixel_size.label("height"),
            GenerationItem.created_at.label("created_at"),
        )
        .join(GenerationJob, GenerationItem.job_id == GenerationJob.id)
        .where(
            GenerationJob.user_id == user_id,
            GenerationJob.status == JobStatus.completed,
            GenerationItem.output_image_url.isnot(None),
        )
    )

    return union_all(creations_q, gen_items_q).subquery()


async def get_gallery_count(session: AsyncSession, user_id: int) -> int:
    """Return total number of gallery items for a user."""
    combined = _build_combined_query(user_id)
    result = await session.execute(
        select(func.count()).select_from(combined)
    )
    return result.scalar() or 0


async def get_gallery_items(
    session: AsyncSession,
    user_id: int,
    *,
    limit: int = 30,
    offset: int = 0,
) -> list[dict]:
    """Return paginated gallery items for a user, sorted by newest first."""
    combined = _build_combined_query(user_id)
    result = await session.execute(
        select(combined)
        .order_by(desc(combined.c.created_at))
        .limit(limit)
        .offset(offset)
    )
    return [
        {
            "id": row.id,
            "source": row.source,
            "description": row.description,
            "output_image_url": row.output_image_url,
            "width": row.width,
            "height": row.height,
            "created_at": row.created_at,
        }
        for row in result.all()
    ]
