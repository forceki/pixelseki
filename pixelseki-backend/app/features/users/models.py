from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _next_monday() -> datetime:
    """Return next Monday 00:00 UTC."""
    now = datetime.now(timezone.utc)
    days_ahead = (7 - now.weekday()) % 7  # 0=Monday
    if days_ahead == 0:
        days_ahead = 7
    return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Profile
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Third-party provider
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Credits
    generation_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    credits_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_next_monday
    )

    # Cumulative token usage
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Status & timestamps
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
