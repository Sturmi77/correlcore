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
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user, get_current_verified_user
from app.core.auth_cookies import clear_auth_cookies
from app.db.redis_client import TokenStore, get_redis
from app.db.session import get_session
from app.models.user import User
from app.schemas.consent import (
    ConsentListResponse,
    ConsentRecordRequest,
    ConsentRecordResponse,
    ConsentRevokeRequest,
)
from app.schemas.sync import SyncConflictListItem, SyncConflictListResponse, SyncEntityType
from app.schemas.user import DeleteAccountRequest
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.schemas.user_profile import UserProfileResponse, UserProfileUpsert
from app.services.consent_service import (
    list_consent_history,
    record_consent,
    revoke_consent,
    summarize_current_consents,
)
from app.services.export_service import build_export_envelope, export_filename, render_export_zip
from app.services.note_markers import list_user_marker_suggestions
from app.services.sync_conflict_service import list_sync_conflicts, sanitize_conflict_value
from app.services.user_preferences_service import (
    get_or_create_user_preferences,
    update_user_preferences,
)
from app.services.user_profile_service import get_or_create_user_profile, upsert_user_profile
from app.services.user_service import UserDeletionError, delete_user_account

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/me/consents",
    response_model=ConsentListResponse,
    summary="List consent history and current states for the current user",
)
async def list_my_consents(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> ConsentListResponse:
    history = await list_consent_history(db, user_id=current_user.id)
    return ConsentListResponse(
        current=summarize_current_consents(history),
        history=[ConsentRecordResponse.model_validate(row) for row in history],
    )


@router.post(
    "/me/consents",
    response_model=ConsentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a consent grant or revocation",
)
async def record_my_consent(
    payload: ConsentRecordRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> ConsentRecordResponse:
    entry = await record_consent(db, user_id=current_user.id, payload=payload)
    return ConsentRecordResponse.model_validate(entry)


@router.post(
    "/me/consents/revoke",
    response_model=ConsentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Revoke a previously granted consent",
)
async def revoke_my_consent(
    payload: ConsentRevokeRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> ConsentRecordResponse:
    history = await list_consent_history(db, user_id=current_user.id)
    current = summarize_current_consents(history)
    match = next((item for item in current if item.consent_type == payload.type.strip()), None)
    version = match.consent_version if match and match.consent_version else "1"
    entry = await revoke_consent(
        db,
        user_id=current_user.id,
        consent_type=payload.type.strip(),
        consent_version=version,
    )
    return ConsentRecordResponse.model_validate(entry)


@router.get(
    "/me/note-markers/suggestions",
    response_model=list[str],
    summary="Return recent custom note markers for chip suggestions",
)
async def list_my_note_marker_suggestions(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[str]:
    return await list_user_marker_suggestions(db, user_id=current_user.id)


@router.get(
    "/preferences",
    response_model=UserPreferencesResponse,
    summary="Return the current user's preference state",
)
async def get_my_preferences(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> UserPreferencesResponse:
    preferences = await get_or_create_user_preferences(db, user_id=current_user.id)
    return UserPreferencesResponse.model_validate(preferences)


@router.patch(
    "/preferences",
    response_model=UserPreferencesResponse,
    summary="Update the current user's preference state",
)
async def update_my_preferences(
    payload: UserPreferencesUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> UserPreferencesResponse:
    preferences = await update_user_preferences(db, user_id=current_user.id, payload=payload)
    return UserPreferencesResponse.model_validate(preferences)


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    summary="Upsert the current user's optional onboarding profile",
)
async def put_my_profile(
    payload: UserProfileUpsert,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> UserProfileResponse:
    profile = await upsert_user_profile(db, user_id=current_user.id, payload=payload)
    return UserProfileResponse.model_validate(profile)


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Return the current user's optional onboarding profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> UserProfileResponse:
    profile = await get_or_create_user_profile(db, user_id=current_user.id)
    return UserProfileResponse.model_validate(profile)


@router.get(
    "/sync-conflicts",
    response_model=SyncConflictListResponse,
    summary="List sync merge conflicts for the current user (read-only)",
)
async def list_my_sync_conflicts(
    entity_type: SyncEntityType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> SyncConflictListResponse:
    rows, total = await list_sync_conflicts(
        db,
        user_id=current_user.id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    items = [
        SyncConflictListItem(
            id=row.id,
            entity_id=row.entity_id,
            entity_type=row.entity_type,  # type: ignore[arg-type]
            field_name=row.field_name,
            client_ts=row.client_ts,
            server_ts=row.server_ts,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
            client_value=sanitize_conflict_value(row.field_name, row.client_value),
            server_value=sanitize_conflict_value(row.field_name, row.server_value),
        )
        for row in rows
    ]
    return SyncConflictListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/export",
    summary="Download the current user's portable data export (DSGVO Art. 20)",
)
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    envelope = await build_export_envelope(db, user=current_user)
    return Response(
        content=render_export_zip(envelope),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{export_filename("zip")}"'},
    )


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

    clear_auth_cookies(response)
    # 204 No Content — the response body must be empty per RFC 7231.
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
