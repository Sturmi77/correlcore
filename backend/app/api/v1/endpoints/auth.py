"""Auth endpoints — register, login, refresh, logout, me.

Cookie strategy (ADR-0004):
- Access token:  HttpOnly, Secure, SameSite=strict, Path=/api, max_age=15 min
- Refresh token: HttpOnly, Secure, SameSite=strict, Path=/api/v1/auth/refresh, max_age=30 days

Scoping the refresh cookie to /api/v1/auth/refresh ensures it is only sent
on the single endpoint that needs it, reducing the attack surface.

Rate-limiting (SlowAPI):
- POST /register: 5 requests / minute per IP → 429 on breach (Issue #65, SA-2)
- POST /login:    5 requests / minute per IP → 429 on breach
- POST /resend-verification: 3 requests / minute per IP
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.redis_client import TokenStore, get_redis
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    AuthError,
    EmailNotVerifiedError,
    VerificationError,
    login_user,
    logout_user,
    refresh_tokens,
    request_registration,
    request_verification_resend,
    verify_email,
)
from app.services.email_service import (
    send_already_registered_email,
    send_verification_email,
)

logger = logging.getLogger(__name__)
router = APIRouter()

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


_REGISTER_GENERIC_MESSAGE = "If the email is not yet registered, a verification mail has been sent."


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register a new user (always returns 202 to prevent enumeration)",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Enumeration-safe registration endpoint (Issue #65, SA-1/SA-2).

    Always responds with the same generic 202 message regardless of
    whether the email is new or already registered, so an attacker
    cannot distinguish the two cases from HTTP status, body, or timing
    above the SMTP background task. The branch is decided in
    :func:`request_registration`; mail dispatch happens asynchronously.

    Rate-limit: 5 requests per minute per IP.
    """
    outcome = await request_registration(db, data)

    if outcome.action == "created":
        # Plaintext-Token nur im Background-Task an den Mail-Versand weiterreichen.
        # SMTP-Fehler werden im EmailService geloggt, blocken aber nicht die
        # Registrierung (Issue #39).
        assert outcome.verification_token is not None  # narrows type for mypy
        background_tasks.add_task(
            send_verification_email,
            to_email=outcome.user.email,
            display_name=outcome.user.display_name,
            token=outcome.verification_token,
        )
    else:
        # action == "already_registered": kein neuer User, keine Verify-Mail.
        # Stattdessen einmalige "Bereits registriert"-Notiz an die Adresse.
        background_tasks.add_task(
            send_already_registered_email,
            to_email=outcome.user.email,
            display_name=outcome.user.display_name,
        )

    return MessageResponse(message=_REGISTER_GENERIC_MESSAGE)


# ---------------------------------------------------------------------------
# POST /verify-email  (Issue #39)
# ---------------------------------------------------------------------------


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify a user's email via the token from the welcome mail",
)
async def verify_email_endpoint(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await verify_email(db, data.token)
    except VerificationError as exc:
        # Always 400 with a generic message — see service docstring
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MessageResponse(message="Email verified. You can now sign in.")


# ---------------------------------------------------------------------------
# POST /resend-verification  (Issue #39, rate-limited)
# ---------------------------------------------------------------------------


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resend a verification email (always returns 202 to avoid enumeration)",
)
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    result = await request_verification_resend(db, data.email)
    if result is not None:
        user, plaintext_token = result
        background_tasks.add_task(
            send_verification_email,
            to_email=user.email,
            display_name=user.display_name,
            token=plaintext_token,
        )
    # Same response whether or not an email exists — prevents enumeration
    return MessageResponse(
        message="If the email is registered and unverified, a verification mail has been sent."
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
    except EmailNotVerifiedError as exc:
        # 403 → frontend shows 'resend verification' UI (see auth.login.error_unverified)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        ) from exc
    except AuthError as exc:
        # Generic message — no user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
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
