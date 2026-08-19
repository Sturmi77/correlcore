"""Public instance descriptor (#734/#735).

``GET /api/v1/instance`` lets the web bundle discover, at runtime, whether it
is talking to the managed SaaS (``hosted``) or a self-hosted deployment, and
whether anonymous self-registration is open. The same web artifact can then
present an account-signup CTA or a self-host CTA without a build-time flag or a
separate build per mode.

Public and dependency-free by design — it exposes only non-sensitive
deployment facts and must be reachable before login (the anonymous landing
reads it).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class InstanceInfo(BaseModel):
    """Non-sensitive, public deployment descriptor."""

    mode: Literal["hosted", "selfhost"]
    registration_enabled: bool
    version: str


@router.get(
    "",
    response_model=InstanceInfo,
    summary="Public instance descriptor",
    description=(
        "Runtime deployment facts for the web client: managed SaaS vs. "
        "self-host, whether self-registration is open, and the running version. "
        "Public — safe to call before authentication."
    ),
    tags=["internal"],
)
async def instance_info() -> InstanceInfo:
    return InstanceInfo(
        mode="hosted" if settings.DEPLOYMENT_MODE == "hosted" else "selfhost",
        registration_enabled=settings.REGISTRATION_ENABLED,
        version=settings.APP_VERSION,
    )
