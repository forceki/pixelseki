import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CreationCategory(str, enum.Enum):
    character = "character"
    background = "background"
    place = "place"
    environment = "environment"
    item = "item"
    other = "other"


class CreationStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Creation(Base):
    __tablename__ = "creations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Content
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[CreationCategory] = mapped_column(
        Enum(CreationCategory, name="creation_category", native_enum=True),
        nullable=False,
        default=CreationCategory.other,
    )
    direction: Mapped[str] = mapped_column(String(50), nullable=False, default="none")

    # Dimensions
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=64)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=64)
    transparent_bg: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Reference
    reference_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # AI Provider
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="gemini")

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("creations.id", ondelete="SET NULL"), nullable=True
    )

    # Output
    original_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Status
    status: Mapped[CreationStatus] = mapped_column(
        Enum(CreationStatus, name="creation_status", native_enum=True),
        nullable=False,
        default=CreationStatus.pending,
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
