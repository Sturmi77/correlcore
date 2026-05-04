"""Pydantic schemas for auth endpoints.

Privacy note: UserResponse never exposes hashed_password or internal flags
beyond what is needed by the client (id, email, display_name, is_verified).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Basic strength check — at least one digit and one letter."""
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Client sends the refresh token in the request body as fallback.
    Primary path is the HttpOnly cookie — body field is optional."""

    refresh_token: str | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_verified: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Access token returned in body; refresh token set as HttpOnly cookie."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
