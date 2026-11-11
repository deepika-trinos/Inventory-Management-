"""Request and response shapes for login."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "admin@example.com", "password": "your-password"}]}
    )

    email: str = Field(min_length=3, max_length=255, description="Login email (not case-sensitive).")
    password: str = Field(min_length=1, max_length=256, description="Account password.")


class TokenResponse(BaseModel):
    access_token: str = Field(description="Send as:  Authorization: Bearer <access_token>")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the token expires.")
