import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssetType(str, enum.Enum):
    object = "object"
    tileset = "tileset"


class CameraView(str, enum.Enum):
    side_view = "side_view"
    top_down = "top_down"
    isometric = "isometric"


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Display name (editable by user)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # UI Tab Selection
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="job_asset_type", native_enum=True), nullable=False
    )

    # Configuration
    directions: Mapped[str] = mapped_column(String(50), nullable=False)
    camera_view: Mapped[CameraView] = mapped_column(
        Enum(CameraView, name="job_camera_view", native_enum=True), nullable=False
    )
    pixel_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Prompts & References
    global_description: Mapped[str] = mapped_column(Text, nullable=False)
    style_reference_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # AI Provider
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="gemini")

    # Cost & Status
    token_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=True),
        nullable=False,
        default=JobStatus.pending,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    items: Mapped[list["GenerationItem"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="GenerationItem.item_index"
    )


class GenerationItem(Base):
    __tablename__ = "generation_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tag: Mapped[str] = mapped_column(String(50), nullable=False, default="original")
    edit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redo_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Output
    original_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    job: Mapped["GenerationJob"] = relationship(back_populates="items")
