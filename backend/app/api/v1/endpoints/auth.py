"""Auth endpoints — register, login, refresh, logout, me.

Cookie strategy (ADR-0004):
- Access token:  HttpOnly, Secure, SameSite=strict, Path=/api, max_age=15 min
- Refresh token: HttpOnly, Secure, SameSite=strict, Path=/api/v1/auth/refresh, max_age=30 days

Scoping the refresh cookie to /api/v1/auth/refresh ensures it is only sent
to endpoints under that path, reducing the attack surface. Browser logout
must therefore use POST /auth/refresh/logout (not /auth/logout) so the
HttpOnly refresh cookie is attached and Redis can revoke the JTI.

Rate-limiting (SlowAPI):
- POST /register: 5 requests / minute per IP → 429 on breach (Issue #65, SA-2)
- POST /login:    5 requests / minute per IP → 429 on breach
- POST /verify-email: 10 requests / minute per IP → 429 on breach
- POST /forgot-password: 3 requests / minute per IP → 429 on breach
- POST /reset-password: 10 requests / minute per IP → 429 on breach
- POST /resend-verification: 3 requests / minute per IP
- POST /refresh: 30 requests / minute per IP
- POST /logout and /refresh/logout: 20 requests / minute per IP
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
from app.core.auth_cookies import (
    ACCESS_COOKIE_MAX_AGE_SECONDS,
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    set_auth_cookies,
)
from app.core.rate_limit import limiter
from app.db.redis_client import TokenStore, get_redis
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    AuthError,
    EmailNotVerifiedError,
    PasswordResetError,
    VerificationError,
    issue_session_tokens,
    login_user,
    logout_user,
    refresh_tokens,
    request_password_reset,
    request_registration,
    request_verification_resend,
    reset_password,
    verify_email,
)
from app.services.email_service import (
    send_already_registered_email,
    send_password_reset_email,
    send_verification_email,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _wants_access_token_in_body(request: Request) -> bool:
    """Opt-in for API scripts / Capacitor Bearer path; browsers use cookies only."""
    raw = request.query_params.get("include_access_token", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _token_response(
    request: Request,
    *,
    access: str,
    refresh: str,
    user: User,
    allow_body_tokens: bool | None = None,
) -> TokenResponse:
    """Build TokenResponse; include JWT pair only when client opts in.

    ``allow_body_tokens`` defaults to the ``include_access_token`` query flag.
    Cookie-sourced refresh must pass ``False`` so HttpOnly refresh cannot be
    exfiltrated into a JS-readable body (Capacitor uses body refresh instead).
    """
    include = (
        _wants_access_token_in_body(request) if allow_body_tokens is None else allow_body_tokens
    )
    return TokenResponse(
        access_token=access if include else None,
        refresh_token=refresh if include else None,
        expires_in=ACCESS_COOKIE_MAX_AGE_SECONDS,
        user=UserResponse.model_validate(user),
    )


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
    response_model=TokenResponse,
    response_model_exclude_none=True,
    summary="Verify email and establish an authenticated session",
)
@limiter.limit("10/minute")
async def verify_email_endpoint(
    request: Request,
    data: VerifyEmailRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    try:
        user = await verify_email(db, data.token)
    except VerificationError as exc:
        # Always 400 with a generic message — see service docstring
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    token_store = TokenStore(redis)
    access, refresh = await issue_session_tokens(token_store, user)
    # Email verify establishes a session — default persistent (remember on).
    set_auth_cookies(response, access, refresh, remember_me=True, request=request)
    return _token_response(request, access=access, refresh=refresh, user=user)


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
# POST /forgot-password  (O-20)
# ---------------------------------------------------------------------------

_FORGOT_PASSWORD_GENERIC_MESSAGE = (
    "If the email is registered, a password reset mail has been sent."
)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password reset email (always returns 202)",
)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    result = await request_password_reset(db, data.email)
    if result is not None:
        user, plaintext_token = result
        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            display_name=user.display_name,
            token=plaintext_token,
        )
    return MessageResponse(message=_FORGOT_PASSWORD_GENERIC_MESSAGE)


# ---------------------------------------------------------------------------
# POST /reset-password  (O-20)
# ---------------------------------------------------------------------------


@router.post(
    "/reset-password",
    response_model=TokenResponse,
    response_model_exclude_none=True,
    summary="Reset password and establish an authenticated session",
)
@limiter.limit("10/minute")
async def reset_password_endpoint(
    request: Request,
    data: ResetPasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    try:
        user = await reset_password(db, data.token, data.password)
    except PasswordResetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    token_store = TokenStore(redis)
    await token_store.revoke_all(str(user.id))
    access, refresh = await issue_session_tokens(token_store, user)
    # Password reset establishes a session — default persistent (remember on).
    set_auth_cookies(response, access, refresh, remember_me=True, request=request)
    return _token_response(request, access=access, refresh=refresh, user=user)


# ---------------------------------------------------------------------------
# POST /login  (rate-limited: 5/min per IP)
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
    response_model_exclude_none=True,
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
    set_auth_cookies(response, access, refresh, remember_me=data.remember_me, request=request)
    return _token_response(request, access=access, refresh=refresh, user=user)


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------


@router.post(
    "/refresh",
    response_model=TokenResponse,
    response_model_exclude_none=True,
    summary="Rotate refresh token and get a new access token",
)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    # Cookie vs body selection:
    # - Browser: cookie only, no include_access_token → cookie path, no body JWTs.
    # - Capacitor: body refresh_token + ?include_access_token=true → body path,
    #   return JWTs in JSON even if a leftover HttpOnly cookie is also present
    #   (credentials:omit should omit cookies, but Android WebViews have been
    #   observed sending them anyway; cookie-wins previously cleared Bearer
    #   tokens client-side after a 200 with an empty body).
    cookie_token = request.cookies.get(REFRESH_COOKIE_NAME)
    body_token = body.refresh_token
    wants_body = _wants_access_token_in_body(request)
    token: str | None
    used_cookie: bool
    if wants_body and body_token:
        token = body_token
        used_cookie = False
    else:
        token = cookie_token or body_token
        used_cookie = cookie_token is not None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    token_store = TokenStore(redis)
    try:
        access, new_refresh, user = await refresh_tokens(db, token_store, token)
    except AuthError as exc:
        clear_auth_cookies(response, request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    # v1: refresh re-issues persistent cookies. Session cookies (remember off)
    # already die with the browser process; see PERSISTENT_SESSION_PLAN.md.
    set_auth_cookies(response, access, new_refresh, remember_me=True, request=request)
    # Never emit JWTs in the JSON body when refresh came from the HttpOnly
    # cookie — even if ?include_access_token=true (XSS / same-origin script).
    allow_body = wants_body and not used_cookie
    return _token_response(
        request,
        access=access,
        refresh=new_refresh,
        user=user,
        allow_body_tokens=allow_body,
    )


# ---------------------------------------------------------------------------
# POST /logout and POST /refresh/logout
# ---------------------------------------------------------------------------


async def _logout_and_clear(
    request: Request,
    response: Response,
    body: RefreshRequest,
    redis: aioredis.Redis,
) -> MessageResponse:
    """Revoke refresh JTI when present, then clear auth cookies.

    Browser clients must call the ``/refresh/logout`` route so the
    path-scoped ``refresh_token`` cookie is included. Native clients can
    use ``/logout`` with a JSON body token.
    """
    token = request.cookies.get(REFRESH_COOKIE_NAME) or body.refresh_token
    if token:
        token_store = TokenStore(redis)
        await logout_user(token_store, token)
    clear_auth_cookies(response, request=request)
    return MessageResponse(message="Logged out successfully")


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Invalidate refresh token and clear cookies (body/native)",
)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    redis: aioredis.Redis = Depends(get_redis),
) -> MessageResponse:
    return await _logout_and_clear(request, response, body, redis)


@router.post(
    "/refresh/logout",
    response_model=MessageResponse,
    summary="Invalidate refresh token and clear cookies (browser cookie path)",
)
@limiter.limit("20/minute")
async def logout_via_refresh_cookie_path(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    redis: aioredis.Redis = Depends(get_redis),
) -> MessageResponse:
    """Browser logout under the refresh cookie path.

    ``refresh_token`` is Path=/api/v1/auth/refresh, so browsers never send
    it to ``POST /auth/logout``. This route receives the cookie and
    revokes the Redis JTI before clearing Set-Cookie.
    """
    return await _logout_and_clear(request, response, body, redis)


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
