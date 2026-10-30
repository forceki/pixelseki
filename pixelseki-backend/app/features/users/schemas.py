from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None
    avatar_url: str | None
    generation_credits: int
    credits_reset_at: datetime
    total_input_tokens: int
    total_output_tokens: int

    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
