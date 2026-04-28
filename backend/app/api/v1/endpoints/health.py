"""Internal health check endpoint for API v1."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns API health status."""
    return HealthResponse(status="ok", version="0.0.1")
