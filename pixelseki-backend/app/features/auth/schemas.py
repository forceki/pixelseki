from pydantic import BaseModel

from app.features.users.schemas import UserResponse


class GoogleLoginRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
