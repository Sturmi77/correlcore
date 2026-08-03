"""M2 user data export service.

The export intentionally omits internal IDs and ``user_id`` values. It
uses those identifiers only while assembling entry-tag and entry-symptom
relationships in memory.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.insight import Insight
from app.models.insight_dismissal import InsightDismissal
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.export import ExportEnvelope, ExportScoreLegendItem, ExportUser
from app.services.insight_dismissal_service import migrate_uuid_prefs_to_subject_dismissals
from app.services.insight_service import _tag_slugs_for_legacy_insights, insight_subject_key

EXPORT_FORMAT_VERSION = "1.4"
_EXPORT_OMIT_KEYS = frozenset(
    {
        "id",
        "user_id",
        "entry_id",
        "tag_id",
        "symptom_id",
        "insight_id",
        "subject_id",
    }
)
_UUID_IN_TEXT = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
APP_EXPORT_VERSION = "1.2.0"
SCORE_LEGEND: dict[str, ExportScoreLegendItem] = {
    "mood_score": ExportScoreLegendItem(
        min=1,
        max=5,
        min_label="very bad",
        max_label="very good",
    ),
    "energy": ExportScoreLegendItem(
        min=1,
        max=5,
        min_label="drained",
        max_label="full of energy",
    ),
    "stress": ExportScoreLegendItem(
        min=1,
        max=5,
        min_label="relaxed",
        max_label="very stressed",
    ),
}
CSV_SCORE_LEGENDS = {
    key: f"{value.min}={value.min_label}; {value.max}={value.max_label}"
    for key, value in SCORE_LEGEND.items()
}


def export_filename(extension: str, *, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).date().isoformat()
    return f"correlcore-export-{stamp}.{extension}"


def _jsonable_without_ids(value: Any) -> Any:
    """Serialize nested values while omitting internal IDs / UUID leaves."""
    if isinstance(value, uuid.UUID):
        return None
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key in _EXPORT_OMIT_KEYS or isinstance(item, uuid.UUID):
                continue
            cleaned[key] = _jsonable_without_ids(item)
        return cleaned
    if isinstance(value, list):
        return [_jsonable_without_ids(item) for item in value if not isinstance(item, uuid.UUID)]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _enum_value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    return str(enum_value) if enum_value is not None else str(value)


def _export_subject_key(subject_key: str) -> str:
    """Redact embedded UUIDs so exports omit internal database IDs."""

    return _UUID_IN_TEXT.sub("<id>", subject_key)


async def build_export_envelope(db: AsyncSession, *, user: User) -> ExportEnvelope:
    entries_result = await db.execute(
        select(Entry)
        .where(Entry.user_id == user.id)
        .order_by(Entry.entry_date.asc(), Entry.slot.asc())
    )
    entries = list(entries_result.scalars().all())
    entry_ids = [entry.id for entry in entries]
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()

    tags_by_entry: dict[uuid.UUID, list[dict[str, Any]]] = defaultdict(list)
    symptoms_by_entry: dict[uuid.UUID, list[dict[str, Any]]] = defaultdict(list)

    visible_tags: dict[tuple[str, str], dict[str, Any]] = {}
    visible_symptoms: dict[tuple[str, str], dict[str, Any]] = {}

    if entry_ids:
        tag_rows = await db.execute(
            select(EntryTag.entry_id, Tag)
            .join(Tag, Tag.id == EntryTag.tag_id)
            .where(EntryTag.user_id == user.id, EntryTag.entry_id.in_(entry_ids))
            .order_by(Tag.category.asc(), Tag.slug.asc())
        )
        for entry_id, tag in tag_rows.all():
            payload = {
                "slug": tag.slug,
                "name": tag.name,
                "category": tag.category.value,
                "color": tag.color,
                "is_default": tag.is_default,
            }
            tags_by_entry[entry_id].append(payload)
            visible_tags[(tag.slug, tag.category.value)] = payload

        symptom_rows = await db.execute(
            select(EntrySymptom.entry_id, EntrySymptom.intensity, Symptom)
            .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
            .where(EntrySymptom.user_id == user.id, EntrySymptom.entry_id.in_(entry_ids))
            .order_by(Symptom.slug.asc())
        )
        for entry_id, intensity, symptom in symptom_rows.all():
            name = symptom.display_name
            payload = {
                "slug": symptom.slug,
                "name": name,
                "icon": symptom.icon,
                "is_default": symptom.is_default,
            }
            symptoms_by_entry[entry_id].append({**payload, "intensity": intensity})
            visible_symptoms[(symptom.slug, name)] = payload

    from app.models.entry import NoteVisibility

    exported_entries: list[dict[str, Any]] = []
    for entry in entries:
        visibility = getattr(entry, "note_visibility", NoteVisibility.FULL)
        visibility_value = (
            visibility.value if isinstance(visibility, NoteVisibility) else str(visibility)
        )
        note_hidden = visibility_value == NoteVisibility.HIDDEN.value
        exported_entries.append(
            {
                "date": entry.entry_date.isoformat(),
                "slot": entry.slot.value,
                "mood_score": entry.mood_score,
                "energy": entry.energy,
                "stress": entry.stress,
                "cycle_day": entry.cycle_day,
                "cycle_bleeding_level": (
                    entry.cycle_bleeding_level.value
                    if entry.cycle_bleeding_level is not None
                    else None
                ),
                "sleep_minutes": entry.sleep_minutes,
                "sleep_quality": entry.sleep_quality,
                "work_context": entry.work_context.value,
                "source": entry.source.value,
                "note": None if note_hidden else entry.note_enc,
                "note_visibility": visibility_value,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "tags": tags_by_entry.get(entry.id, []),
                "symptoms": symptoms_by_entry.get(entry.id, []),
            }
        )

    insights_result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user.id)
        .order_by(Insight.generated_for_date.asc(), Insight.generated_at.asc())
    )
    insights = list(insights_result.scalars().all())
    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, insights)

    await migrate_uuid_prefs_to_subject_dismissals(db, user_id=user.id)

    dismissals_result = await db.execute(
        select(InsightDismissal)
        .where(InsightDismissal.user_id == user.id)
        .order_by(InsightDismissal.dismissed_at.asc())
    )
    dismissals = list(dismissals_result.scalars().all())
    dismissed_subject_keys = {row.subject_key for row in dismissals}

    exported_insights: list[dict[str, Any]] = []
    for insight in insights:
        subject_key = insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)
        exported_insights.append(
            {
                "insight_type": _enum_value(insight.insight_type),
                "tier": _enum_value(insight.tier),
                "metric": insight.metric,
                "subject_type": insight.subject_type,
                "subject_label": insight.subject_label,
                "subject_key": _export_subject_key(subject_key),
                "effect_size": insight.effect_size,
                "confidence": insight.confidence,
                "sample_n": insight.sample_n,
                "statement": insight.statement_enc,
                "flags": _jsonable_without_ids(insight.flags or {}),
                "payload": _jsonable_without_ids(insight.payload or {}),
                "visibility": ("dismissed" if subject_key in dismissed_subject_keys else "active"),
                "generated_for_date": insight.generated_for_date.isoformat(),
                "generated_at": insight.generated_at.isoformat(),
                "created_at": insight.created_at.isoformat(),
                "updated_at": insight.updated_at.isoformat(),
            }
        )

    exported_dismissals = [
        {
            "subject_key": _export_subject_key(row.subject_key),
            "dismissed_at": row.dismissed_at.isoformat(),
            "created_at": row.created_at.isoformat(),
        }
        for row in dismissals
    ]

    return ExportEnvelope(
        export_date=datetime.now(UTC),
        app_version=APP_EXPORT_VERSION,
        format_version=EXPORT_FORMAT_VERSION,
        score_legend=SCORE_LEGEND,
        user=ExportUser(
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
        ),
        entries=exported_entries,
        tags=sorted(visible_tags.values(), key=lambda item: (item["category"], item["slug"])),
        symptoms=sorted(visible_symptoms.values(), key=lambda item: item["slug"]),
        habits=[],
        profile=(
            {
                "sleep_hours_typical": (
                    profile.sleep_hours_typical.value
                    if profile.sleep_hours_typical is not None
                    else None
                ),
                "work_context_typical": (
                    profile.work_context_typical.value
                    if profile.work_context_typical is not None
                    else None
                ),
                "sport_frequency": (
                    profile.sport_frequency.value if profile.sport_frequency is not None else None
                ),
                "insight_curiosity": (
                    profile.insight_curiosity.value
                    if profile.insight_curiosity is not None
                    else None
                ),
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            }
            if profile is not None
            else None
        ),
        insights=exported_insights,
        insight_dismissals=exported_dismissals,
        photos=[],
        sleep=[
            {
                "date": entry.entry_date.isoformat(),
                "slot": entry.slot.value,
                "sleep_minutes": entry.sleep_minutes,
                "sleep_quality": entry.sleep_quality,
                "source": entry.source.value,
            }
            for entry in entries
            if entry.sleep_minutes is not None or entry.sleep_quality is not None
        ],
    )


def render_export_json(envelope: ExportEnvelope) -> bytes:
    payload = envelope.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def render_export_csv(envelope: ExportEnvelope) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=[
            "date",
            "slot",
            "mood_score",
            "energy",
            "stress",
            "cycle_day",
            "cycle_bleeding_level",
            "sleep_minutes",
            "sleep_quality",
            "mood_scale",
            "energy_scale",
            "stress_scale",
            "work_context",
            "note",
            "tags",
            "symptoms",
            "created_at",
            "updated_at",
        ],
    )
    writer.writeheader()
    for entry in envelope.entries:
        writer.writerow(
            {
                "date": entry["date"],
                "slot": entry["slot"],
                "mood_score": entry["mood_score"],
                "energy": entry["energy"],
                "stress": entry["stress"],
                "cycle_day": entry.get("cycle_day") or "",
                "cycle_bleeding_level": entry.get("cycle_bleeding_level") or "",
                "sleep_minutes": (
                    "" if entry.get("sleep_minutes") is None else entry["sleep_minutes"]
                ),
                "sleep_quality": (
                    "" if entry.get("sleep_quality") is None else entry["sleep_quality"]
                ),
                "mood_scale": CSV_SCORE_LEGENDS["mood_score"],
                "energy_scale": CSV_SCORE_LEGENDS["energy"],
                "stress_scale": CSV_SCORE_LEGENDS["stress"],
                "work_context": entry["work_context"],
                "note": entry["note"] or "",
                "tags": ", ".join(tag["name"] for tag in entry["tags"]),
                "symptoms": ", ".join(
                    f"{symptom['name']}:{symptom['intensity']}" for symptom in entry["symptoms"]
                ),
                "created_at": entry["created_at"],
                "updated_at": entry["updated_at"],
            }
        )
    return out.getvalue().encode("utf-8-sig")


def render_export_zip(envelope: ExportEnvelope) -> bytes:
    readme = (
        "CorrelCore data export\n"
        "====================\n\n"
        "This archive contains your CorrelCore data in machine-readable JSON.\n"
        "It may include sensitive health-related information. Store it carefully.\n\n"
        "Files:\n"
        "- export.json: entries, assigned tags, assigned symptoms, insights, "
        "insight dismissals, and account metadata.\n"
        "- README.txt: this format note.\n\n"
        "Score scales:\n"
        "- mood_score: 1=very bad; 5=very good.\n"
        "- energy: 1=drained; 5=full of energy.\n"
        "- stress: 1=relaxed; 5=very stressed.\n\n"
        "insights: full insight history (active and hidden), including decrypted "
        "statements. insight_dismissals: subject-stable hide intents.\n"
        "sleep: per-day manual sleep records (sleep_minutes 0..1440, sleep_quality "
        "1..5); the same values also appear on each entry. Sections for photos and "
        "habits remain empty arrays until those features ship in the product.\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export.json", render_export_json(envelope))
        archive.writestr("README.txt", readme)
    return buffer.getvalue()
