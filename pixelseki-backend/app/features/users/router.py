from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.features.users.schemas import UserProfileResponse, UserUpdateRequest
from app.features.users.services import get_user_by_id, update_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user = await get_user_by_id(session, int(current_user["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user = await get_user_by_id(session, int(current_user["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user = await update_user(session, user, **body.model_dump(exclude_unset=True))
    return user
