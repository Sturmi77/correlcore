"""User self-management endpoints.

Currently exposes a single endpoint, ``DELETE /api/v1/user/me``, the
DSGVO-Art.-17-Erasure-API (Issue #66, ADR-0005, M1-Quality-Gate-Finding
SA-4).

Why ``/user/me`` and not ``/user/account``
------------------------------------------
The codebase already exposes ``GET /api/v1/auth/me`` for "the current
user". Mirroring that with ``/user/me`` keeps the URL hierarchy
consistent and intuitive, and matches the intent stated in
``DESIGN_DOCUMENT.md §9``. The historical ``/user/account`` reference
in ADR-0005 / DSGVO.md / ARCHITECTURE.md is updated alongside this
change so the documentation is consistent again.

Why this is a separate router from ``/auth``
--------------------------------------------
``/auth`` is the *authentication* surface (sessions, tokens, email
verification). Account-level self-management (delete, future export)
is the *user* surface and lives behind a different mental model — even
though the implementation reuses the auth dependency for "who is
calling".
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user
from app.db.redis_client import TokenStore, get_redis
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import DeleteAccountRequest
from app.services.user_service import UserDeletionError, delete_user_account

logger = logging.getLogger(__name__)
router = APIRouter()

_ACCESS_COOKIE = "access_token"
_REFRESH_COOKIE = "refresh_token"


def _clear_auth_cookies(response: Response) -> None:
    """Mirror of ``app.api.v1.endpoints.auth._clear_auth_cookies``.

    Duplicated intentionally to keep the user-router free of imports
    from the auth-router module (one-way dependency: user can call into
    auth deps, but auth cannot call into user). The two helpers must
    keep their cookie paths in sync — the auth cookies are scoped to
    ``/api`` and ``/api/v1/auth/refresh`` respectively.
    """
    response.delete_cookie(_ACCESS_COOKIE, path="/api")
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth/refresh")


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete the current user's account (DSGVO Art. 17 erasure)",
    responses={
        204: {"description": "Account deleted, cookies cleared, refresh tokens revoked."},
        401: {"description": "Missing/invalid auth token, or password did not match."},
    },
)
async def delete_my_account(
    body: DeleteAccountRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> Response:
    """Erase the calling user's account and all dependent data.

    Behaviour:

    - Auth required (``get_current_user``). ``is_verified`` is **not**
      required: an unverified user must also be able to exercise their
      Art.-17 right to be forgotten without first jumping through email
      verification.
    - Re-authentication: the request body must include the current
      password. A wrong password is reported as ``401 Unauthorized``
      with the same generic message used by the login endpoint — we do
      not leak whether the password mismatched or some other auth check
      failed.
    - On success the row is hard-deleted; ``ON DELETE CASCADE`` removes
      all ``entries`` / ``tags`` / ``symptoms`` / ``entry_tags`` /
      ``entry_symptoms`` / ``email_verification_tokens`` /
      ``user_encryption_keys`` rows owned by the user. The wrapped DEK
      going away is what makes ``entries.note_enc`` and Custom-
      ``symptoms.name_enc`` ciphertexts cryptographically unrecoverable.
    - Refresh tokens are revoked in Redis in the same call so the user
      is force-logged out from every device.
    - Auth cookies on the *response* are cleared so the calling browser
      does not retain a bound-to-deleted-user session.
    """
    try:
        await delete_user_account(db, TokenStore(redis), current_user, body.password)
    except UserDeletionError as exc:
        # Generic 401 — same shape and message used elsewhere in /auth
        # so observers cannot distinguish "wrong password" from "stale
        # token" by response body.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from exc

    _clear_auth_cookies(response)
    # 204 No Content — the response body must be empty per RFC 7231.
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
