import logging
import uuid

from app.core.broker import broker
from app.core.database import async_session_factory
from app.core.errors import humanize_error

# Import all models so SQLAlchemy resolves foreign keys in the worker process
from app.features.users.models import User  # noqa: F401
from app.features.generations.models import GenerationJob, GenerationItem  # noqa: F401
from app.features.generations.log_model import GeminiLog  # noqa: F401
from app.features.creations.models import Creation  # noqa: F401

from app.features.generations.models import JobStatus
from app.features.creations.models import CreationStatus
from app.features.generations.services import get_item_by_id, get_job_by_id, regenerate_item, run_generation
from app.features.creations.services import get_creation_by_id, run_creation

logger = logging.getLogger(__name__)


@broker.task
async def generate_pixel_art_task(job_id: str) -> None:
    """Background task: run Gemini generation for a job."""
    logger.info("Worker picked up job %s", job_id)

    async with async_session_factory() as session:
        job = await get_job_by_id(session, uuid.UUID(job_id))
        if not job:
            logger.error("Job %s not found in DB", job_id)
            return

        try:
            await run_generation(session, job)
            logger.info("Worker finished job %s — status: %s", job_id, job.status)
        except Exception as e:
            logger.error("Worker task for job %s crashed: %s", job_id, e)
            error_msg = humanize_error(e)
            for item in job.items:
                if item.status in ("pending", "processing"):
                    item.status = "failed"
                    item.error_message = error_msg
            job.status = JobStatus.failed
            await session.commit()


@broker.task
async def regenerate_item_task(job_id: str, item_id: str) -> None:
    """Background task: regenerate a single item."""
    logger.info("Worker regenerating item %s for job %s", item_id, job_id)

    async with async_session_factory() as session:
        job = await get_job_by_id(session, uuid.UUID(job_id))
        if not job:
            logger.error("Job %s not found in DB", job_id)
            return

        item = await get_item_by_id(session, uuid.UUID(item_id))
        if not item:
            logger.error("Item %s not found in DB", item_id)
            return

        try:
            await regenerate_item(session, job, item)
            logger.info("Worker finished regenerating item %s", item_id)
        except Exception as e:
            logger.error("Worker task for item %s crashed: %s", item_id, e)
            item.status = "failed"
            item.error_message = humanize_error(e)
            await session.commit()


@broker.task
async def run_creation_task(creation_id: str) -> None:
    """Background task: run Gemini generation for a creation."""
    logger.info("Worker picked up creation %s", creation_id)

    async with async_session_factory() as session:
        creation = await get_creation_by_id(session, uuid.UUID(creation_id))
        if not creation:
            logger.error("Creation %s not found in DB", creation_id)
            return

        try:
            await run_creation(session, creation)
            logger.info("Worker finished creation %s — status: %s", creation_id, creation.status)
        except Exception as e:
            logger.error("Worker task for creation %s crashed: %s", creation_id, e)
            creation.status = CreationStatus.failed
            await session.commit()
