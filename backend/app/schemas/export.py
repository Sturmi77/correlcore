"""Schemas for M2 data export."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExportUser(BaseModel):
    email: str
    display_name: str | None
    created_at: datetime


class ExportEnvelope(BaseModel):
    export_date: datetime
    moodsync_version: str
    format_version: str = "1.0"
    user: ExportUser
    entries: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[dict[str, Any]] = Field(default_factory=list)
    symptoms: list[dict[str, Any]] = Field(default_factory=list)
    habits: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    photos: list[dict[str, Any]] = Field(default_factory=list)
    sleep: list[dict[str, Any]] = Field(default_factory=list)
