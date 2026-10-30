from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.features.users.services import create_user, get_user_by_google_id, update_user


async def handle_google_login(session: AsyncSession, user_info: dict) -> dict:
    """Find or create user from Google profile, return JWT + user data."""
    google_id = user_info["sub"]
    email = user_info["email"]
    name = user_info.get("name")
    avatar_url = user_info.get("picture")

    user = await get_user_by_google_id(session, google_id)

    if user:
        user = await update_user(session, user, name=name, email=email, avatar_url=avatar_url)
    else:
        user = await create_user(
            session, email=email, name=name, avatar_url=avatar_url, google_id=google_id
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "generation_credits": user.generation_credits,
            "credits_reset_at": user.credits_reset_at.isoformat(),
            "total_input_tokens": user.total_input_tokens,
            "total_output_tokens": user.total_output_tokens,
        },
    }
