"""Pydantic schemas for auth endpoints.

Privacy note: UserResponse never exposes hashed_password or internal flags
beyond what is needed by the client (id, email, display_name, is_verified).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_serializer

from app.core.password_policy import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    validate_password_strength,
)

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    # Cap length to bound bcrypt CPU cost; strength rules apply on register/reset only.
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    # Issue #453 — persistent session („Angemeldet bleiben“). Default on.
    # Web/PWA: persistent vs session cookies; Capacitor: secure-store vs memory.
    remember_me: bool = True


class RefreshRequest(BaseModel):
    """Client sends the refresh token in the request body as fallback.
    Primary path is the HttpOnly cookie — body field is optional."""

    refresh_token: str | None = None


class VerifyEmailRequest(BaseModel):
    """Issue #39: payload for POST /auth/verify-email.

    Token is sent in the JSON body (not the URL) so it doesn't end up
    in access logs / browser history when the frontend forwards it.
    """

    token: str = Field(min_length=16, max_length=128)


class ResendVerificationRequest(BaseModel):
    """Issue #39: payload for POST /auth/resend-verification."""

    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """O-20: payload for POST /auth/forgot-password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """O-20: payload for POST /auth/reset-password."""

    token: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


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
    """Session response after login / refresh / verify / reset.

    Browser clients rely on HttpOnly cookies. ``access_token`` /
    ``refresh_token`` are omitted by default (XSS surface) and only included
    when the client opts in via ``?include_access_token=true`` (API scripts /
    Capacitor Bearer path, ADR-0006).
    """

    model_config = ConfigDict(extra="forbid")

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse

    @model_serializer(mode="wrap")
    def _omit_null_tokens(self, handler):  # type: ignore[no-untyped-def]
        data = handler(self)
        if data.get("access_token") is None:
            data.pop("access_token", None)
        if data.get("refresh_token") is None:
            data.pop("refresh_token", None)
        return data


class MessageResponse(BaseModel):
    message: str
