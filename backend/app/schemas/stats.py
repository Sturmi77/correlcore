"""Pydantic schemas for M2 visualization statistics."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field

from app.models.tag import TagCategory

TimeseriesRange = Literal["week", "month", "quarter", "year"]
TagCooccurrenceRange = Literal["7d", "30d", "90d", "1y"]

COOCCURRENCE_RANGE_DAYS: dict[TagCooccurrenceRange, int] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
}


class TimeseriesPoint(BaseModel):
    period_start: date_type
    period_end: date_type
    entry_count: int
    mood_avg: float | None = None
    energy_avg: float | None = None
    stress_avg: float | None = None
    sleep_quality_avg: float | None = None


class TimeseriesResponse(BaseModel):
    range: TimeseriesRange
    points: list[TimeseriesPoint]


class TagHeatmapDay(BaseModel):
    date: date_type
    count: int


class TagHeatmapTag(BaseModel):
    tag_id: uuid.UUID
    slug: str
    name: str
    category: TagCategory
    color: str | None = None
    days: list[TagHeatmapDay] = Field(default_factory=list)


class TagHeatmapResponse(BaseModel):
    start_date: date_type
    end_date: date_type
    tags: list[TagHeatmapTag] = Field(default_factory=list)


class SymptomHeatmapDay(BaseModel):
    date: date_type
    count: int
    max_intensity: int


class SymptomHeatmapSymptom(BaseModel):
    symptom_id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None
    days: list[SymptomHeatmapDay] = Field(default_factory=list)


class SymptomHeatmapResponse(BaseModel):
    start_date: date_type
    end_date: date_type
    symptoms: list[SymptomHeatmapSymptom] = Field(default_factory=list)


class EntryStreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_entry_days: int
    last_entry_date: date_type | None = None
    as_of: date_type


class TagCooccurrenceTagRef(BaseModel):
    tag_id: uuid.UUID
    slug: str
    name: str
    category: TagCategory
    color: str | None = None


class TagCooccurrencePair(BaseModel):
    tag_a: TagCooccurrenceTagRef
    tag_b: TagCooccurrenceTagRef
    count: int = Field(ge=1)
    pct_of_a: float = Field(ge=0, le=100)
    pct_of_b: float = Field(ge=0, le=100)


class TagCooccurrenceResponse(BaseModel):
    range: TagCooccurrenceRange
    start_date: date_type
    end_date: date_type
    min_count: int = Field(ge=1)
    pairs: list[TagCooccurrencePair] = Field(default_factory=list)


class SymptomTagCooccurrenceSymptomRef(BaseModel):
    symptom_id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None


class SymptomTagCooccurrenceCell(BaseModel):
    symptom: SymptomTagCooccurrenceSymptomRef
    tag: TagCooccurrenceTagRef
    phi: float
    jaccard: float = Field(ge=0, le=1)
    lift: float = Field(ge=0)
    co_count: int = Field(ge=1)
    symptom_count: int = Field(ge=1)
    tag_count: int = Field(ge=1)
    total_count: int = Field(ge=1)
    p_value_corrected: float = Field(ge=0, le=1)
    confounder: str | None = None


class SymptomTagCooccurrenceResponse(BaseModel):
    range: TagCooccurrenceRange
    start_date: date_type
    end_date: date_type
    min_count: int = Field(ge=1)
    cells: list[SymptomTagCooccurrenceCell] = Field(default_factory=list)


class TagClusterMember(BaseModel):
    kind: Literal["tag", "symptom"]
    signal_id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None
    category: str | None = None
    color: str | None = None


class TagClusterGroup(BaseModel):
    cluster_id: int = Field(ge=1)
    label: str
    tags: list[TagCooccurrenceTagRef] = Field(default_factory=list)
    members: list[TagClusterMember] = Field(default_factory=list)
    cluster_kind: Literal["tags_only", "mixed"] = "tags_only"
    strength: float = Field(ge=0, le=1)


TagClusterMaturity = Literal["early", "provisional", "robust"]
TagClusterMode = Literal["pair", "kmeans"]


class TagClustersResponse(BaseModel):
    status: Literal["ok", "insufficient_data"]
    entry_count: int = Field(ge=0)
    active_tag_count: int = Field(ge=0)
    active_signal_count: int = Field(ge=0)
    window_days: int = Field(ge=1)
    k: int | None = Field(default=None, ge=1)
    reason: str | None = None
    cluster_kind: Literal["tags_only", "mixed"] = "tags_only"
    cluster_maturity: TagClusterMaturity | None = None
    cluster_mode: TagClusterMode | None = None
    entries_until_robust: int | None = Field(default=None, ge=0)
    silhouette_score: float | None = None
    clusters: list[TagClusterGroup] = Field(default_factory=list)
    # Transparency (#706): how many groups are shown after the strength floor +
    # display cap, how many active signals ended up in no shown group, and the
    # sample-size-aware floor that was applied (so clients can derive strength
    # bands without duplicating the calibrated constants).
    shown_cluster_count: int = Field(default=0, ge=0)
    omitted_signal_count: int = Field(default=0, ge=0)
    strength_floor: float = Field(default=0.0, ge=0, le=1)
