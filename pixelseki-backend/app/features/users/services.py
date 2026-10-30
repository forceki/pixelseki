from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import User, _next_monday

DEFAULT_CREDITS = 5


async def maybe_reset_credits(session: AsyncSession, user: User) -> User:
    """Reset credits to default if the reset date has passed."""
    now = datetime.now(timezone.utc)
    if now >= user.credits_reset_at:
        user.generation_credits = DEFAULT_CREDITS
        user.credits_reset_at = _next_monday()
        await session.commit()
        await session.refresh(user)
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user = await maybe_reset_credits(session, user)
    return user


async def get_user_by_google_id(session: AsyncSession, google_id: str) -> User | None:
    result = await session.execute(select(User).where(User.google_id == google_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    name: str | None = None,
    avatar_url: str | None = None,
    google_id: str | None = None,
) -> User:
    user = User(email=email, name=name, avatar_url=avatar_url, google_id=google_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    user: User,
    **kwargs,
) -> User:
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user
