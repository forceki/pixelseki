"""Storage abstraction — local disk or AWS S3.

When S3_BUCKET is set, files are stored in S3 and paths like /{prefix}/... are saved in DB.
The full public URL is built at runtime via resolve_url().
When S3_BUCKET is empty, files go to local app/static/ and paths are /static/...
"""

import logging
from pathlib import Path

import os

# Prevent boto3 from reading ~/.aws/credentials (use .env keys only)
os.environ["AWS_SHARED_CREDENTIALS_FILE"] = ""
os.environ["AWS_CONFIG_FILE"] = ""

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from app.core.config import settings

logger = logging.getLogger(__name__)

# Local fallback directory
LOCAL_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
LOCAL_STATIC_DIR.mkdir(parents=True, exist_ok=True)

# S3 client (lazy init)
_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        )
    return _s3_client


def _use_s3() -> bool:
    return bool(settings.S3_BUCKET)


def _s3_key(relative_path: str) -> str:
    """Build the S3 object key from a relative path like 'generations/{id}/file.png'."""
    prefix = settings.S3_PREFIX.strip("/")
    return f"{prefix}/{relative_path}" if prefix else relative_path


def _base_url() -> str:
    """Get the base assets URL — from env or auto-build from S3 config."""
    if settings.BASE_ASSETS_URL:
        return settings.BASE_ASSETS_URL.rstrip("/")
    if _use_s3():
        return f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com"
    return ""


def resolve_url(db_path: str | None) -> str:
    """Resolve a stored DB path to a full public URL.

    DB stores:
      - S3:   "/{prefix}/generations/{id}/file.png"
      - Local: "/static/generations/{id}/file.png"

    Returns:
      - S3:   "{BASE_ASSETS_URL}/{prefix}/..."
      - Local: "/static/..." (unchanged)
    """
    if not db_path:
        return ""

    base = _base_url()
    if base and not db_path.startswith("http"):
        return f"{base}{db_path}"

    return db_path


def save_file(relative_path: str, data: bytes, content_type: str = "image/png") -> str:
    """Save file and return a DB-storable path.

    Returns:
        "/{prefix}/generations/{id}/file.png" (S3)
        or "/static/generations/{id}/file.png" (local).
    """
    if _use_s3():
        key = _s3_key(relative_path)
        _get_s3().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info("S3 upload: %s (%d bytes)", key, len(data))
        return f"/{key}"

    # Local fallback
    local_path = LOCAL_STATIC_DIR / relative_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    return f"/static/{relative_path}"


def read_file(db_path: str) -> bytes | None:
    """Read file bytes from S3 or local disk using a DB-stored path."""
    if _use_s3():
        key = _path_to_s3_key(db_path)
        try:
            resp = _get_s3().get_object(Bucket=settings.S3_BUCKET, Key=key)
            return resp["Body"].read()
        except ClientError:
            logger.warning("S3 read failed: %s", key)
            return None

    # Local fallback
    rel = _path_to_local(db_path)
    local_path = LOCAL_STATIC_DIR / rel
    if local_path.exists():
        return local_path.read_bytes()
    return None


def file_exists(db_path: str) -> bool:
    """Check if a file exists in S3 or local disk."""
    if _use_s3():
        key = _path_to_s3_key(db_path)
        try:
            _get_s3().head_object(Bucket=settings.S3_BUCKET, Key=key)
            return True
        except ClientError:
            return False

    rel = _path_to_local(db_path)
    return (LOCAL_STATIC_DIR / rel).exists()


def _path_to_s3_key(db_path: str) -> str:
    """Convert a DB path to an S3 object key.

    "/{prefix}/generations/{id}/file.png" -> "{prefix}/generations/{id}/file.png"
    "/static/generations/{id}/file.png"   -> "{prefix}/generations/{id}/file.png"
    """
    # Already an S3-style path: /{prefix}/...
    prefix = settings.S3_PREFIX.strip("/")
    if prefix and db_path.startswith(f"/{prefix}/"):
        return db_path.lstrip("/")

    # Legacy /static/ path
    if db_path.startswith("/static/"):
        rel = db_path[len("/static/"):]
        return _s3_key(rel)

    # Full S3 URL (legacy)
    if db_path.startswith("https://"):
        idx = db_path.find(".com/")
        if idx != -1:
            return db_path[idx + 5:]

    return db_path.lstrip("/")


def _path_to_local(db_path: str) -> str:
    """Convert a DB path to a local relative path under static/.

    "/static/generations/{id}/file.png" -> "generations/{id}/file.png"
    """
    if db_path.startswith("/static/"):
        return db_path[len("/static/"):]
    return db_path.lstrip("/")
