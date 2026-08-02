"""Health Connect import endpoint (M8 Sprint 4, #172).

Sleep-only import from the Android Health Connect bridge. Gated by the DSGVO
Art. 9 consent (Issue #31); the per-field toggle and manual-wins merge live in
the import service. Requires an active *and verified* user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.consent_log import CONSENT_TYPE_HEALTH_CONNECT
from app.models.user import User
from app.schemas.health_connect import HealthConnectImportRequest, HealthConnectImportResponse
from app.services.consent_service import is_consent_granted
from app.services.health_connect_import_service import import_health_connect_sleep

router = APIRouter()


@router.post(
    "/import",
    response_model=HealthConnectImportResponse,
    summary="Import Health Connect sleep into existing entries",
)
@limiter.limit("30/minute")
async def import_health_connect_endpoint(
    request: Request,
    payload: HealthConnectImportRequest,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> HealthConnectImportResponse:
    granted = await is_consent_granted(
        db, user_id=user.id, consent_type=CONSENT_TYPE_HEALTH_CONNECT
    )
    if not granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="health_connect_consent_required",
        )
    return await import_health_connect_sleep(db, user_id=user.id, items=payload.sleep)
