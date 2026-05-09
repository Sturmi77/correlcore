"""M2 user data export service.

The export intentionally omits internal IDs and ``user_id`` values. It
uses those identifiers only while assembling entry-tag and entry-symptom
relationships in memory.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag
from app.models.user import User
from app.schemas.export import ExportEnvelope, ExportUser

EXPORT_FORMAT_VERSION = "1.0"
MOODSYNC_EXPORT_VERSION = "0.0.1"


def export_filename(extension: str, *, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).date().isoformat()
    return f"moodsync-export-{stamp}.{extension}"


async def build_export_envelope(db: AsyncSession, *, user: User) -> ExportEnvelope:
    entries_result = await db.execute(
        select(Entry)
        .where(Entry.user_id == user.id)
        .order_by(Entry.entry_date.asc(), Entry.slot.asc())
    )
    entries = list(entries_result.scalars().all())
    entry_ids = [entry.id for entry in entries]

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

    exported_entries: list[dict[str, Any]] = []
    for entry in entries:
        exported_entries.append(
            {
                "date": entry.entry_date.isoformat(),
                "slot": entry.slot.value,
                "mood_score": entry.mood_score,
                "energy": entry.energy,
                "stress": entry.stress,
                "work_context": entry.work_context.value,
                "note": entry.note_enc,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "tags": tags_by_entry.get(entry.id, []),
                "symptoms": symptoms_by_entry.get(entry.id, []),
            }
        )

    return ExportEnvelope(
        export_date=datetime.now(UTC),
        moodsync_version=MOODSYNC_EXPORT_VERSION,
        format_version=EXPORT_FORMAT_VERSION,
        user=ExportUser(
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
        ),
        entries=exported_entries,
        tags=sorted(visible_tags.values(), key=lambda item: (item["category"], item["slug"])),
        symptoms=sorted(visible_symptoms.values(), key=lambda item: item["slug"]),
        habits=[],
        insights=[],
        photos=[],
        sleep=[],
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
        "MoodSync data export\n"
        "====================\n\n"
        "This archive contains your MoodSync data in machine-readable JSON.\n"
        "It may include sensitive health-related information. Store it carefully.\n\n"
        "Files:\n"
        "- export.json: entries, assigned tags, assigned symptoms and account metadata.\n"
        "- README.txt: this format note.\n\n"
        "Sections for photos, habits, insights and sleep are present as empty arrays until those "
        "features exist in the product.\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export.json", render_export_json(envelope))
        archive.writestr("README.txt", readme)
    return buffer.getvalue()
