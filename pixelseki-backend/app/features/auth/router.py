from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.features.auth.schemas import GoogleLoginRequest, TokenResponse
from app.features.auth.services import handle_google_login

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/google/login", response_model=TokenResponse)
async def google_login(
    body: GoogleLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Verify Google id_token from frontend, create/update user, return JWT."""
    try:
        user_info = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    return await handle_google_login(session, user_info)
