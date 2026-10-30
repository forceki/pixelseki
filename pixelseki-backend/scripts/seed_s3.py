"""
Seed S3: Upload all files from app/static/ to S3 and update database URLs.

Usage:
    python -m scripts.seed_s3
    python -m scripts.seed_s3 --dry-run     # preview without uploading
"""

import argparse
import asyncio
import mimetypes
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.storage import save_file, _use_s3, _s3_key

STATIC_DIR = Path(__file__).resolve().parent.parent / "app" / "static"


def collect_files() -> list[tuple[str, Path]]:
    """Collect all files under app/static/ with their relative paths."""
    files = []
    for root, _, filenames in os.walk(STATIC_DIR):
        for filename in filenames:
            if filename.startswith("."):
                continue
            full_path = Path(root) / filename
            relative = full_path.relative_to(STATIC_DIR)
            files.append((str(relative), full_path))
    return sorted(files)


def guess_content_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def upload_files(files: list[tuple[str, Path]], dry_run: bool = False) -> int:
    """Upload files to S3. Returns count of uploaded files."""
    uploaded = 0
    for relative_path, full_path in files:
        content_type = guess_content_type(full_path.name)
        size = full_path.stat().st_size
        size_kb = size / 1024

        if dry_run:
            print(f"  [DRY RUN] {relative_path} ({size_kb:.1f} KB) -> s3://{settings.S3_BUCKET}/{_s3_key(relative_path)}")
        else:
            data = full_path.read_bytes()
            url = save_file(relative_path, data, content_type=content_type)
            print(f"  Uploaded {relative_path} ({size_kb:.1f} KB) -> {url}")
        uploaded += 1

    return uploaded


async def update_database_urls():
    """Update all /static/... URLs in the database to S3 URLs."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.features.users.models import User  # noqa: F401 — register FK target
    from app.features.generations.models import GenerationJob, GenerationItem
    from app.features.generations.log_model import GeminiLog  # noqa: F401
    from app.features.creations.models import Creation

    S3_HOST = f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com"
    prefix = settings.S3_PREFIX.strip("/")

    def normalize(url: str) -> str:
        """Strip full S3 host or /static/ prefix, return /{prefix}/... path."""
        # Full S3 URL -> relative path
        if url.startswith(S3_HOST):
            return url[len(S3_HOST):]  # already has leading /
        # /static/... -> /{prefix}/...
        if url.startswith("/static/"):
            rel = url[len("/static/"):]
            key = f"{prefix}/{rel}" if prefix else rel
            return f"/{key}"
        return url

    async with async_session_factory() as session:
        # GenerationJob.style_reference_url
        result = await session.execute(
            select(GenerationJob).where(
                GenerationJob.style_reference_url.like("/static/%")
                | GenerationJob.style_reference_url.like(f"{S3_HOST}%")
            )
        )
        jobs = result.scalars().all()
        for job in jobs:
            job.style_reference_url = normalize(job.style_reference_url)
        if jobs:
            print(f"  Updated {len(jobs)} generation job reference URLs")

        # GenerationItem.original_image_url & output_image_url
        result = await session.execute(
            select(GenerationItem).where(
                GenerationItem.original_image_url.like("/static/%")
                | GenerationItem.original_image_url.like(f"{S3_HOST}%")
                | GenerationItem.output_image_url.like("/static/%")
                | GenerationItem.output_image_url.like(f"{S3_HOST}%")
            )
        )
        items = result.scalars().all()
        for item in items:
            if item.original_image_url:
                item.original_image_url = normalize(item.original_image_url)
            if item.output_image_url:
                item.output_image_url = normalize(item.output_image_url)
        if items:
            print(f"  Updated {len(items)} generation item URLs")

        # Creation URLs
        result = await session.execute(
            select(Creation).where(
                Creation.original_image_url.like("/static/%")
                | Creation.original_image_url.like(f"{S3_HOST}%")
                | Creation.output_image_url.like("/static/%")
                | Creation.output_image_url.like(f"{S3_HOST}%")
                | Creation.reference_image_url.like("/static/%")
                | Creation.reference_image_url.like(f"{S3_HOST}%")
            )
        )
        creations = result.scalars().all()
        for c in creations:
            if c.original_image_url:
                c.original_image_url = normalize(c.original_image_url)
            if c.output_image_url:
                c.output_image_url = normalize(c.output_image_url)
            if c.reference_image_url:
                c.reference_image_url = normalize(c.reference_image_url)
        if creations:
            print(f"  Updated {len(creations)} creation URLs")

        await session.commit()
        print("  Database URLs updated successfully")


def main():
    parser = argparse.ArgumentParser(description="Upload app/static/ to S3 and update DB URLs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--skip-db", action="store_true", help="Skip database URL update")
    parser.add_argument("--db-only", action="store_true", help="Only update database URLs (skip file upload)")
    args = parser.parse_args()

    if not _use_s3():
        print("ERROR: S3_BUCKET is not configured in .env")
        print("Set S3_BUCKET, S3_REGION, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY")
        sys.exit(1)

    print(f"S3 Bucket: {settings.S3_BUCKET}")
    print(f"S3 Region: {settings.S3_REGION}")
    print(f"S3 Prefix: {settings.S3_PREFIX}")
    print()

    if not args.db_only:
        # Collect files
        files = collect_files()
        total_size = sum(f.stat().st_size for _, f in files)
        print(f"Found {len(files)} files ({total_size / 1024 / 1024:.1f} MB)")
        print()

        # Upload
        print("Uploading files to S3...")
        uploaded = upload_files(files, dry_run=args.dry_run)
        print(f"\n{'Would upload' if args.dry_run else 'Uploaded'} {uploaded} files")

    # Update DB
    if not args.dry_run and not args.skip_db:
        print("\nUpdating database URLs...")
        asyncio.run(update_database_urls())

    print("\nDone!")


if __name__ == "__main__":
    main()
