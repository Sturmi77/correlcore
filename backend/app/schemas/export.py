"""Schemas for M2 data export."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExportUser(BaseModel):
    email: str
    display_name: str | None
    created_at: datetime


class ExportScoreLegendItem(BaseModel):
    min: int
    max: int
    min_label: str
    max_label: str


class ExportEnvelope(BaseModel):
    export_date: datetime
    app_version: str
    format_version: str = "1.2"
    score_legend: dict[str, ExportScoreLegendItem]
    user: ExportUser
    entries: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[dict[str, Any]] = Field(default_factory=list)
    symptoms: list[dict[str, Any]] = Field(default_factory=list)
    habits: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    photos: list[dict[str, Any]] = Field(default_factory=list)
    sleep: list[dict[str, Any]] = Field(default_factory=list)
