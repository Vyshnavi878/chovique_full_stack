from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshTokenResponse(BaseModel):
    message: str


class MessageResponse(BaseModel):
    message: str
    dev_otp: str | None = None