"""Auth endpoints — register, login, refresh, logout, me.

Cookie strategy (ADR-0004):
- Access token:  HttpOnly, Secure, SameSite=strict, Path=/api, max_age=15 min
- Refresh token: HttpOnly, Secure, SameSite=strict, Path=/api/v1/auth/refresh, max_age=30 days

Scoping the refresh cookie to /api/v1/auth/refresh ensures it is only sent
on the single endpoint that needs it, reducing the attack surface.

Rate-limiting (SlowAPI):
- POST /login: 5 requests / minute per IP → 429 on breach
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.redis_client import TokenStore, get_redis
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    AuthError,
    RegistrationError,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
)
from app.api.v1.deps.auth import get_current_user

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)
router = APIRouter()

limiter = Limiter(key_func=get_remote_address)

_ACCESS_COOKIE = "access_token"
_REFRESH_COOKIE = "refresh_token"
_ACCESS_MAX_AGE = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
_REFRESH_MAX_AGE = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86_400


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=_ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api",
        max_age=_ACCESS_MAX_AGE,
    )
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth/refresh",
        max_age=_REFRESH_MAX_AGE,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(_ACCESS_COOKIE, path="/api")
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth/refresh")


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await register_user(db, data)
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    # TODO M1: send verification email
    return MessageResponse(
        message="Registration successful. Please verify your email address."
    )


# ---------------------------------------------------------------------------
# POST /login  (rate-limited: 5/min per IP)
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive access + refresh tokens",
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    token_store = TokenStore(redis)
    try:
        access, refresh, user = await login_user(db, token_store, data.email, data.password)
    except AuthError:
        # Generic message — no user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    _set_auth_cookies(response, access, refresh)
    return TokenResponse(
        access_token=access,
        expires_in=_ACCESS_MAX_AGE,
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and get a new access token",
)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    # Prefer HttpOnly cookie, fall back to body (API clients)
    token = request.cookies.get(_REFRESH_COOKIE) or body.refresh_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    token_store = TokenStore(redis)
    try:
        access, new_refresh, user = await refresh_tokens(db, token_store, token)
    except AuthError as exc:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    _set_auth_cookies(response, access, new_refresh)
    return TokenResponse(
        access_token=access,
        expires_in=_ACCESS_MAX_AGE,
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Invalidate refresh token and clear cookies",
)
async def logout(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    redis: aioredis.Redis = Depends(get_redis),
) -> MessageResponse:
    token = request.cookies.get(_REFRESH_COOKIE) or body.refresh_token
    if token:
        token_store = TokenStore(redis)
        await logout_user(token_store, token)
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully")


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user's profile",
)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
