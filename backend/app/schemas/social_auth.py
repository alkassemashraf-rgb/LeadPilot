"""Schemas for social login (Facebook, TikTok) authentication flows."""
from pydantic import BaseModel


class SocialAuthStartResponse(BaseModel):
    authorization_url: str


class SocialAuthCallbackResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    new_user: bool = False
