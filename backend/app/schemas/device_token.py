"""Schemas for device push-token registration (M11 Sprint 5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PushProviderLiteral = Literal["fcm", "unifiedpush"]
PushPlatformLiteral = Literal["android", "ios", "web"]


class DeviceTokenUpsert(BaseModel):
    token: str = Field(min_length=8, max_length=4096)
    provider: PushProviderLiteral = "fcm"
    platform: PushPlatformLiteral = "android"
    device_label: str | None = Field(default=None, max_length=120)


class DeviceTokenDelete(BaseModel):
    token: str = Field(min_length=8, max_length=4096)


class DeviceTokenResponse(BaseModel):
    id: uuid.UUID
    provider: PushProviderLiteral
    platform: PushPlatformLiteral
    device_label: str | None = None
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime


class PushTestResponse(BaseModel):
    sent: int = Field(ge=0)
    skipped: int = Field(ge=0)
    message: str
