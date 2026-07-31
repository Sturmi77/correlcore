"""Offline sync engine — push/pull with field-level LWW (M4.1 Sprint 2, #10)."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entry import Entry, EntrySource
from app.models.symptom import Symptom
from app.models.sync_engine import (
    SyncClientState,
    SyncPushBatch,
    SyncRevisionLog,
    SyncUserRevision,
)
from app.models.tag import EntryTag, Tag, TagCategory
from app.schemas.entry import BACKDATE_DAYS_LIMIT, CLIENT_TZ_AHEAD_SLACK_DAYS
from app.schemas.symptom import SymptomEntry
from app.schemas.sync import (
    SyncChange,
    SyncConflictField,
    SyncConflictReport,
    SyncEntityType,
    SyncEntryPayload,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncSymptomPayload,
    SyncTableName,
    SyncTagPayload,
)
from app.services import entry_service
from app.services.symptom_service import (
    SymptomsNotFoundError,
    assign_symptoms_to_entry,
    list_symptoms_for_entry,
)
from app.services.sync_conflict_service import create_sync_conflict, sanitize_conflict_value
from app.services.tag_service import (
    TagsNotFoundError,
    assign_tags_to_entry,
    list_tags_for_entry,
    visible_tag_predicate,
)

logger = logging.getLogger(__name__)

_CRITICAL_FIELDS = frozenset(
    {
        SyncConflictField.MOOD_SCORE.value,
        SyncConflictField.ENERGY.value,
        SyncConflictField.STRESS.value,
        SyncConflictField.NOTE.value,
        SyncConflictField.SYMPTOMS.value,
    }
)

DEFAULT_PULL_LIMIT = 200
MAX_PULL_LIMIT = 500


class SyncError(Exception):
    """Base class for sync-service errors."""


class SyncBadRequestError(SyncError):
    """Invalid cursor, sequence, or payload."""


def encode_cursor(*, user_rev: int, wall: datetime | None = None) -> str:
    payload = {
        "user_rev": user_rev,
        "wall": (wall or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[int, datetime]:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(cursor + padding)
        payload = json.loads(decoded)
        user_rev = int(payload["user_rev"])
        wall_raw = str(payload["wall"]).replace("Z", "+00:00")
        wall = datetime.fromisoformat(wall_raw)
        if wall.tzinfo is None:
            wall = wall.replace(tzinfo=UTC)
        return user_rev, wall
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SyncBadRequestError("invalid sync cursor") from exc


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _client_wins(client_ts: datetime, server_ts: datetime) -> bool:
    return _ensure_utc(client_ts) > _ensure_utc(server_ts)


def _note_presence_marker(note: str | None) -> dict[str, Any]:
    return {"present": bool(note and str(note).strip())}


def _note_conflict_markers(
    client_note: str | None, server_note: str | None
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return redacted conflict markers when notes differ (including two non-empty texts).

    Presence-only markers collapse distinct notes to ``{"present": true}`` and skip
    conflict logging — use this helper so divergent non-empty notes are recorded.
    """
    client_text = (client_note or "").strip() if client_note else ""
    server_text = (server_note or "").strip() if server_note else ""
    if client_text == server_text:
        return None
    return (
        {"present": bool(client_text), "changed": True},
        {"present": bool(server_text), "changed": True},
    )


def _symptoms_map(rows: list[Any]) -> dict[str, int]:
    return {str(row.symptom_id): int(row.intensity) for row in rows}


def _normalize_symptoms_payload(raw: dict[str, int]) -> dict[str, int]:
    return {str(key): int(value) for key, value in raw.items()}


async def _resolve_sync_tag_ids(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    tag_ids: Sequence[uuid.UUID],
) -> list[uuid.UUID]:
    """Drop unknown/deleted/hidden tags that sync cannot newly assign.

    Offline outbox rows often retain tag IDs after a custom tag was deleted
    (DB cascade clears ``entry_tags``; Dexie is not pruned). Raising
    :class:`TagsNotFoundError` becomes an uncaught 500 and the web client
    never acks the push batch, wedging newer pending changes. Keep IDs that
    are still assignable (visible + not hidden) or already linked on this
    entry (hidden historical retention — same allowlist as
    ``assign_tags_to_entry``).
    """
    if not tag_ids:
        return []

    # Preserve first-seen order while deduping.
    ordered = list(dict.fromkeys(tag_ids))
    target_ids = set(ordered)

    current = await db.execute(
        select(EntryTag.tag_id).where(
            EntryTag.entry_id == entry_id,
            EntryTag.user_id == user_id,
        )
    )
    current_ids = {row[0] for row in current.all()}

    visible = await db.execute(
        select(Tag.id).where(
            Tag.id.in_(target_ids),
            visible_tag_predicate(user_id),
            Tag.is_hidden.is_(False),
        )
    )
    visible_ids = {row[0] for row in visible.all()}
    allowed = visible_ids | (target_ids & current_ids)
    dropped = target_ids - allowed
    if dropped:
        logger.warning(
            "sync.entry.drop_unknown_tags",
            extra={
                "user_id": str(user_id),
                "entry_id": str(entry_id),
                "dropped_count": len(dropped),
            },
        )
    return [tag_id for tag_id in ordered if tag_id in allowed]


async def _resolve_sync_symptoms(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    symptoms: dict[str, int],
) -> dict[str, int]:
    """Drop unknown/deleted symptom IDs (and invalid UUID keys) from sync payloads.

    Same outbox-wedge rationale as :func:`_resolve_sync_tag_ids`: assign
    raises :class:`SymptomsNotFoundError` → uncaught 500 → client never acks.
    """
    if not symptoms:
        return {}

    parsed: dict[uuid.UUID, int] = {}
    invalid_keys = 0
    for key, intensity in symptoms.items():
        try:
            parsed[uuid.UUID(str(key))] = int(intensity)
        except (TypeError, ValueError):
            invalid_keys += 1

    if not parsed:
        if invalid_keys:
            logger.warning(
                "sync.entry.drop_unknown_symptoms",
                extra={
                    "user_id": str(user_id),
                    "entry_id": str(entry_id),
                    "dropped_count": invalid_keys,
                },
            )
        return {}

    visible = await db.execute(
        select(Symptom.id).where(
            Symptom.id.in_(parsed.keys()),
            (Symptom.is_default.is_(True)) | (Symptom.user_id == user_id),
        )
    )
    visible_ids = {row[0] for row in visible.all()}
    dropped = set(parsed.keys()) - visible_ids
    if dropped or invalid_keys:
        logger.warning(
            "sync.entry.drop_unknown_symptoms",
            extra={
                "user_id": str(user_id),
                "entry_id": str(entry_id),
                "dropped_count": len(dropped) + invalid_keys,
            },
        )
    return {str(sid): parsed[sid] for sid in parsed if sid in visible_ids}


async def _get_or_create_user_revision(db: AsyncSession, *, user_id: uuid.UUID) -> SyncUserRevision:
    """Return the per-user revision counter, locking the row for concurrent push/pull."""
    result = await db.execute(
        select(SyncUserRevision).where(SyncUserRevision.user_id == user_id).with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    # No row yet — insert under a nested transaction so a concurrent create
    # does not poison the outer sync session.
    async with db.begin_nested():
        db.add(SyncUserRevision(user_id=user_id, current_rev=0))
        try:
            await db.flush()
        except IntegrityError:
            pass

    result = await db.execute(
        select(SyncUserRevision).where(SyncUserRevision.user_id == user_id).with_for_update()
    )
    return result.scalar_one()


async def _next_user_rev(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    state = await _get_or_create_user_revision(db, user_id=user_id)
    state.current_rev += 1
    state.updated_at = datetime.now(UTC)
    await db.flush()
    return int(state.current_rev)


async def _append_revision_log(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entity_type: SyncEntityType,
    entity_id: uuid.UUID,
    operation: str,
    payload: dict[str, Any],
    entity_updated_at: datetime,
) -> int:
    user_rev = await _next_user_rev(db, user_id=user_id)
    db.add(
        SyncRevisionLog(
            user_id=user_id,
            user_rev=user_rev,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=payload,
            entity_updated_at=_ensure_utc(entity_updated_at),
        )
    )
    await db.flush()
    return user_rev


async def _get_client_state(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
) -> SyncClientState:
    result = await db.execute(
        select(SyncClientState).where(
            SyncClientState.user_id == user_id,
            SyncClientState.client_id == client_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    row = SyncClientState(user_id=user_id, client_id=client_id, last_applied_seq=0)
    db.add(row)
    await db.flush()
    return row


async def _get_existing_batch(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> SyncPushBatch | None:
    result = await db.execute(
        select(SyncPushBatch).where(
            SyncPushBatch.user_id == user_id,
            SyncPushBatch.client_id == client_id,
            SyncPushBatch.batch_id == batch_id,
        )
    )
    return result.scalar_one_or_none()


def _entry_payload_from_model(
    entry: Entry,
    *,
    tag_ids: list[uuid.UUID],
    symptoms: dict[str, int],
    for_revision_log: bool = False,
) -> dict[str, Any]:
    """Build entry sync payload. Revision-log rows must not store plaintext notes."""
    note_value = None if for_revision_log else entry.note_enc
    return {
        "entry_date": entry.entry_date.isoformat(),
        "slot": entry.slot.value,
        "mood_score": entry.mood_score,
        "energy": entry.energy,
        "stress": entry.stress,
        "cycle_day": entry.cycle_day,
        "cycle_bleeding_level": (
            entry.cycle_bleeding_level.value if entry.cycle_bleeding_level is not None else None
        ),
        "work_context": entry.work_context.value,
        "note": note_value,
        "tag_ids": [str(tag_id) for tag_id in tag_ids],
        "symptoms": symptoms,
    }


async def _hydrate_entry_pull_payload(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entity_id: uuid.UUID,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Attach live note text to pull deltas; revision log stores note=None only."""
    result = await db.execute(select(Entry).where(Entry.id == entity_id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return data
    hydrated = dict(data)
    hydrated["note"] = entry.note_enc
    return hydrated


def _revision_to_change(row: SyncRevisionLog) -> SyncChange:
    return SyncChange(
        seq=int(row.user_rev),
        id=row.entity_id,
        table=_entity_type_to_table(row.entity_type),
        operation=row.operation,  # type: ignore[arg-type]
        data=row.payload,
        updated_at=row.entity_updated_at,
    )


async def _revision_to_pull_change(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    row: SyncRevisionLog,
) -> SyncChange:
    data = dict(row.payload)
    if row.entity_type == "entry" and row.operation == "upsert":
        data = await _hydrate_entry_pull_payload(
            db,
            user_id=user_id,
            entity_id=row.entity_id,
            data=data,
        )
    return SyncChange(
        seq=int(row.user_rev),
        id=row.entity_id,
        table=_entity_type_to_table(row.entity_type),
        operation=row.operation,  # type: ignore[arg-type]
        data=data,
        updated_at=row.entity_updated_at,
    )


def _tag_payload_from_model(tag: Tag) -> dict[str, Any]:
    return {
        "slug": tag.slug,
        "name": tag.name,
        "category": tag.category.value
        if isinstance(tag.category, TagCategory)
        else str(tag.category),
        "icon": tag.icon,
        "color": tag.color,
        "habit_type": tag.habit_type,
        "target_frequency": tag.target_frequency,
    }


def _symptom_payload_from_model(symptom: Symptom) -> dict[str, Any]:
    return {
        "slug": symptom.slug,
        "name": symptom.display_name,
        "icon": symptom.icon,
    }


def _entity_type_to_table(entity_type: str) -> SyncTableName:
    mapping: dict[str, SyncTableName] = {
        "entry": "entries",
        "tag": "tags",
        "symptom": "symptoms",
    }
    return mapping[entity_type]


async def _maybe_conflict(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entity_id: uuid.UUID,
    entity_type: SyncEntityType,
    field_name: str,
    client_ts: datetime,
    server_ts: datetime,
    client_value: dict[str, Any] | None,
    server_value: dict[str, Any] | None,
) -> SyncConflictReport | None:
    if field_name not in _CRITICAL_FIELDS:
        return None
    if client_value == server_value:
        return None

    await create_sync_conflict(
        db,
        user_id=user_id,
        entity_id=entity_id,
        entity_type=entity_type,
        field_name=field_name,
        client_value=client_value,
        server_value=server_value,
        client_ts=client_ts,
        server_ts=server_ts,
    )
    return SyncConflictReport(
        entity_id=entity_id,
        entity_type=entity_type,
        field_name=field_name,
        client_ts=client_ts,
        server_ts=server_ts,
        client_value=sanitize_conflict_value(field_name, client_value),
        server_value=sanitize_conflict_value(field_name, server_value),
    )


async def _merge_entry_upsert(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    change: SyncChange,
) -> list[SyncConflictReport]:
    payload = SyncEntryPayload.model_validate(change.data)
    client_ts = _ensure_utc(change.updated_at)
    # Validate against the client edit day, not wall-clock "today". Offline
    # rows often sit in the outbox past the live 7-day create window; rejecting
    # them here raises SyncBadRequestError for the whole push batch and the
    # web client never acks — wedging newer pending changes behind the stale
    # row. Cap future clock skew so a device clock ahead of UTC cannot open an
    # unbounded backdate window.
    as_of = min(
        client_ts.date(),
        entry_service._today() + timedelta(days=CLIENT_TZ_AHEAD_SLACK_DAYS),
    )
    if not entry_service._within_backdate_window(payload.entry_date, as_of=as_of):
        raise SyncBadRequestError(f"entry_date must be within the last {BACKDATE_DAYS_LIMIT} days")

    result = await db.execute(select(Entry).where(Entry.id == change.id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    conflicts: list[SyncConflictReport] = []

    if entry is None:
        slot_result = await db.execute(
            select(Entry).where(
                Entry.user_id == user_id,
                Entry.entry_date == payload.entry_date,
                Entry.slot == payload.slot,
            )
        )
        entry = slot_result.scalar_one_or_none()

    if entry is None:
        created = False
        async with db.begin_nested():
            entry = Entry(
                id=change.id,
                user_id=user_id,
                entry_date=payload.entry_date,
                slot=payload.slot,
                mood_score=payload.mood_score,
                energy=payload.energy,
                stress=payload.stress,
                cycle_day=payload.cycle_day,
                cycle_bleeding_level=payload.cycle_bleeding_level,
                source=EntrySource.DIRECT,
                work_context=payload.work_context,
                note_enc=payload.note,
                updated_at=client_ts,
            )
            db.add(entry)
            try:
                await db.flush()
                created = True
            except IntegrityError:
                created = False

        if not created:
            # Concurrent create for the same (date, slot) — merge into the winner.
            slot_result = await db.execute(
                select(Entry).where(
                    Entry.user_id == user_id,
                    Entry.entry_date == payload.entry_date,
                    Entry.slot == payload.slot,
                )
            )
            entry = slot_result.scalar_one_or_none()
            if entry is None:
                raise SyncBadRequestError("entry slot collision could not be resolved")
        else:
            # Filter before assign — stale deleted tag/symptom IDs must not 500
            # the whole push batch (web outbox only acks after success).
            tag_ids = await _resolve_sync_tag_ids(
                db, user_id=user_id, entry_id=entry.id, tag_ids=payload.tag_ids
            )
            incoming_symptoms = await _resolve_sync_symptoms(
                db,
                user_id=user_id,
                entry_id=entry.id,
                symptoms=_normalize_symptoms_payload(payload.symptoms),
            )
            await assign_tags_to_entry(
                db,
                user_id=user_id,
                entry_id=entry.id,
                tag_ids=tag_ids,
                record_revision=False,
            )
            symptom_entries = [
                SymptomEntry(symptom_id=uuid.UUID(key), intensity=value)
                for key, value in incoming_symptoms.items()
            ]
            await assign_symptoms_to_entry(
                db,
                user_id=user_id,
                entry_id=entry.id,
                symptoms=symptom_entries,
                record_revision=False,
            )
            await _append_revision_log(
                db,
                user_id=user_id,
                entity_type="entry",
                entity_id=entry.id,
                operation="upsert",
                payload=_entry_payload_from_model(
                    entry,
                    tag_ids=tag_ids,
                    symptoms=incoming_symptoms,
                    for_revision_log=True,
                ),
                entity_updated_at=entry.updated_at,
            )
            return conflicts

    server_ts = _ensure_utc(entry.updated_at)
    current_symptoms = _symptoms_map(
        await list_symptoms_for_entry(db, user_id=user_id, entry_id=entry.id)
    )
    # Drop deleted/unknown association IDs before LWW/conflict so assign cannot
    # abort the batch; compare conflicts against the filtered client map.
    incoming_symptoms = await _resolve_sync_symptoms(
        db,
        user_id=user_id,
        entry_id=entry.id,
        symptoms=_normalize_symptoms_payload(payload.symptoms),
    )
    tag_ids = await _resolve_sync_tag_ids(
        db, user_id=user_id, entry_id=entry.id, tag_ids=payload.tag_ids
    )

    # Slot-merge: client UUID differs from canonical server row — report conflicts
    # against the pending outbox id so the web client can mark the local row.
    conflict_entity_id = change.id if entry.id != change.id else entry.id

    scalar_fields: list[tuple[str, Any, Any, Any]] = [
        ("mood_score", payload.mood_score, entry.mood_score, {"value": entry.mood_score}),
        ("energy", payload.energy, entry.energy, {"value": entry.energy}),
        ("stress", payload.stress, entry.stress, {"value": entry.stress}),
        ("note", payload.note, entry.note_enc, _note_presence_marker(entry.note_enc)),
    ]

    if _client_wins(client_ts, server_ts):
        entry.mood_score = payload.mood_score
        entry.energy = payload.energy
        entry.stress = payload.stress
        entry.cycle_day = payload.cycle_day
        entry.cycle_bleeding_level = payload.cycle_bleeding_level
        entry.work_context = payload.work_context
        entry.note_enc = payload.note
        entry.updated_at = client_ts
        await assign_tags_to_entry(
            db,
            user_id=user_id,
            entry_id=entry.id,
            tag_ids=tag_ids,
            record_revision=False,
        )
        symptom_entries = [
            SymptomEntry(symptom_id=uuid.UUID(key), intensity=value)
            for key, value in incoming_symptoms.items()
        ]
        await assign_symptoms_to_entry(
            db,
            user_id=user_id,
            entry_id=entry.id,
            symptoms=symptom_entries,
            record_revision=False,
        )
        await db.flush()
        tag_ids = [
            tag.id for tag in await list_tags_for_entry(db, user_id=user_id, entry_id=entry.id)
        ]
        symptoms = _symptoms_map(
            await list_symptoms_for_entry(db, user_id=user_id, entry_id=entry.id)
        )
        await _append_revision_log(
            db,
            user_id=user_id,
            entity_type="entry",
            entity_id=entry.id,
            operation="upsert",
            payload=_entry_payload_from_model(
                entry, tag_ids=tag_ids, symptoms=symptoms, for_revision_log=True
            ),
            entity_updated_at=entry.updated_at,
        )
        return conflicts

    for field_name, client_val, _server_val, server_report in scalar_fields:
        if field_name == "note":
            markers = _note_conflict_markers(
                client_val
                if isinstance(client_val, str) or client_val is None
                else str(client_val),
                entry.note_enc,
            )
            if markers is None:
                continue
            client_cmp, server_cmp = markers
        else:
            client_cmp = {"value": client_val}
            server_cmp = server_report
        report = await _maybe_conflict(
            db,
            user_id=user_id,
            entity_id=conflict_entity_id,
            entity_type="entry",
            field_name=field_name,
            client_ts=client_ts,
            server_ts=server_ts,
            client_value=client_cmp,
            server_value=server_cmp,
        )
        if report is not None:
            conflicts.append(report)

    if incoming_symptoms != current_symptoms:
        report = await _maybe_conflict(
            db,
            user_id=user_id,
            entity_id=conflict_entity_id,
            entity_type="entry",
            field_name=SyncConflictField.SYMPTOMS.value,
            client_ts=client_ts,
            server_ts=server_ts,
            client_value={"map": incoming_symptoms},
            server_value={"map": current_symptoms},
        )
        if report is not None:
            conflicts.append(report)

    return conflicts


async def _merge_entry_delete(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    change: SyncChange,
) -> list[SyncConflictReport]:
    result = await db.execute(select(Entry).where(Entry.id == change.id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return []
    client_ts = _ensure_utc(change.updated_at)
    server_ts = _ensure_utc(entry.updated_at)
    if not _client_wins(client_ts, server_ts):
        return []
    await db.delete(entry)
    await db.flush()
    await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="entry",
        entity_id=change.id,
        operation="delete",
        payload={},
        entity_updated_at=_ensure_utc(change.updated_at),
    )
    return []


async def _merge_tag_upsert(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    change: SyncChange,
) -> list[SyncConflictReport]:
    payload = SyncTagPayload.model_validate(change.data)
    client_ts = _ensure_utc(change.updated_at)
    result = await db.execute(select(Tag).where(Tag.id == change.id, Tag.user_id == user_id))
    tag = result.scalar_one_or_none()

    if tag is None:
        tag = Tag(
            id=change.id,
            user_id=user_id,
            slug=payload.slug,
            name=payload.name,
            category=TagCategory(payload.category),
            icon=payload.icon,
            color=payload.color,
            habit_type=payload.habit_type,
            target_frequency=payload.target_frequency,
            is_default=False,
            updated_at=client_ts,
        )
        db.add(tag)
        await db.flush()
    else:
        if tag.is_default:
            raise SyncBadRequestError("default tags cannot be mutated via sync")
        server_ts = _ensure_utc(tag.updated_at)
        if _client_wins(client_ts, server_ts):
            tag.slug = payload.slug
            tag.name = payload.name
            tag.category = TagCategory(payload.category)
            tag.icon = payload.icon
            tag.color = payload.color
            tag.habit_type = payload.habit_type
            tag.target_frequency = payload.target_frequency
            tag.updated_at = client_ts
            await db.flush()
            await _append_revision_log(
                db,
                user_id=user_id,
                entity_type="tag",
                entity_id=tag.id,
                operation="upsert",
                payload=_tag_payload_from_model(tag),
                entity_updated_at=tag.updated_at,
            )
        return []

    await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="tag",
        entity_id=tag.id,
        operation="upsert",
        payload=_tag_payload_from_model(tag),
        entity_updated_at=tag.updated_at,
    )
    return []


async def _merge_tag_delete(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    change: SyncChange,
) -> list[SyncConflictReport]:
    result = await db.execute(
        select(Tag).where(Tag.id == change.id, Tag.user_id == user_id, Tag.is_default.is_(False))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        return []
    await db.delete(tag)
    await db.flush()
    await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="tag",
        entity_id=change.id,
        operation="delete",
        payload={},
        entity_updated_at=_ensure_utc(change.updated_at),
    )
    return []


async def _merge_symptom_upsert(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    change: SyncChange,
) -> list[SyncConflictReport]:
    payload = SyncSymptomPayload.model_validate(change.data)
    client_ts = _ensure_utc(change.updated_at)
    result = await db.execute(
        select(Symptom).where(Symptom.id == change.id, Symptom.user_id == user_id)
    )
    symptom = result.scalar_one_or_none()

    from app.services.slug_hmac import hmac_custom_symptom_slug, is_hmac_symptom_slug

    storage_slug = (
        payload.slug
        if is_hmac_symptom_slug(payload.slug)
        else hmac_custom_symptom_slug(user_id=user_id, semantic_slug=payload.slug)
    )

    if symptom is None:
        symptom = Symptom(
            id=change.id,
            user_id=user_id,
            slug=storage_slug,
            icon=payload.icon,
            is_default=False,
            updated_at=client_ts,
        )
        symptom.set_custom_name(payload.name)
        db.add(symptom)
        await db.flush()
    else:
        if symptom.is_default:
            raise SyncBadRequestError("default symptoms cannot be mutated via sync")
        server_ts = _ensure_utc(symptom.updated_at)
        if _client_wins(client_ts, server_ts):
            symptom.slug = storage_slug
            symptom.icon = payload.icon
            symptom.set_custom_name(payload.name)
            symptom.updated_at = client_ts
            await db.flush()
            await _append_revision_log(
                db,
                user_id=user_id,
                entity_type="symptom",
                entity_id=symptom.id,
                operation="upsert",
                payload=_symptom_payload_from_model(symptom),
                entity_updated_at=symptom.updated_at,
            )
        return []

    await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="symptom",
        entity_id=symptom.id,
        operation="upsert",
        payload=_symptom_payload_from_model(symptom),
        entity_updated_at=symptom.updated_at,
    )
    return []


async def _merge_symptom_delete(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    change: SyncChange,
) -> list[SyncConflictReport]:
    result = await db.execute(
        select(Symptom).where(
            Symptom.id == change.id,
            Symptom.user_id == user_id,
            Symptom.is_default.is_(False),
        )
    )
    symptom = result.scalar_one_or_none()
    if symptom is None:
        return []
    await db.delete(symptom)
    await db.flush()
    await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="symptom",
        entity_id=change.id,
        operation="delete",
        payload={},
        entity_updated_at=_ensure_utc(change.updated_at),
    )
    return []


async def _apply_change(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    change: SyncChange,
) -> list[SyncConflictReport]:
    if change.table == "entries":
        if change.operation == "delete":
            return await _merge_entry_delete(db, user_id=user_id, change=change)
        return await _merge_entry_upsert(db, user_id=user_id, change=change)
    if change.table == "tags":
        if change.operation == "delete":
            return await _merge_tag_delete(db, user_id=user_id, change=change)
        return await _merge_tag_upsert(db, user_id=user_id, change=change)
    if change.table == "symptoms":
        if change.operation == "delete":
            return await _merge_symptom_delete(db, user_id=user_id, change=change)
        return await _merge_symptom_upsert(db, user_id=user_id, change=change)
    raise SyncBadRequestError(f"unsupported sync table: {change.table}")


async def push_changes(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    request: SyncPushRequest,
) -> SyncPushResponse:
    existing = await _get_existing_batch(
        db,
        user_id=user_id,
        client_id=request.client_id,
        batch_id=request.batch_id,
    )
    if existing is not None:
        return SyncPushResponse(
            cursor=existing.cursor,
            applied=existing.applied,
            skipped=existing.skipped,
            conflicts=[SyncConflictReport.model_validate(item) for item in existing.conflicts],
            idempotent_replay=True,
        )

    client_state = await _get_client_state(db, user_id=user_id, client_id=request.client_id)
    sorted_changes = sorted(request.changes, key=lambda item: item.seq)

    applied = 0
    skipped = 0
    conflicts: list[SyncConflictReport] = []

    for change in sorted_changes:
        if change.seq <= client_state.last_applied_seq:
            skipped += 1
            continue
        try:
            conflicts.extend(await _apply_change(db, user_id=user_id, change=change))
        except SyncBadRequestError:
            raise
        except ValidationError as exc:
            raise SyncBadRequestError(str(exc)) from exc
        except (TagsNotFoundError, SymptomsNotFoundError) as exc:
            # Defense in depth: association assign errors must be 400, not 500.
            # Prefer filtering in `_merge_entry_upsert` so the batch still applies;
            # mapping alone does not unblock the web outbox (acks only on success).
            raise SyncBadRequestError(str(exc)) from exc
        applied += 1
        client_state.last_applied_seq = max(client_state.last_applied_seq, change.seq)
        client_state.updated_at = datetime.now(UTC)

    revision = await _get_or_create_user_revision(db, user_id=user_id)
    cursor = encode_cursor(user_rev=int(revision.current_rev))

    response = SyncPushResponse(
        cursor=cursor,
        applied=applied,
        skipped=skipped,
        conflicts=conflicts,
        idempotent_replay=False,
    )

    db.add(
        SyncPushBatch(
            user_id=user_id,
            client_id=request.client_id,
            batch_id=request.batch_id,
            cursor=response.cursor,
            applied=response.applied,
            skipped=response.skipped,
            conflicts=[item.model_dump(mode="json") for item in response.conflicts],
        )
    )
    await db.flush()

    logger.info(
        "sync.push.completed",
        extra={
            "user_id": str(user_id),
            "client_id": str(request.client_id),
            "batch_size": len(request.changes),
            "applied": applied,
            "skipped": skipped,
            "conflict_count": len(conflicts),
        },
    )
    return response


async def record_entry_upsert_revision(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry: Entry,
) -> int:
    """Append a revision-log upsert for an entry mutated via the REST API.

    Sync push already logs after merge; call this from REST create/update and
    association replace-set paths so incremental pull (``since`` set) sees
    online writes after the client's cursor has advanced past initial backfill.

    The per-user revision counter is locked *before* association reads so a
    concurrent REST mutation cannot commit a newer revision between the
    snapshot and this append (stale higher ``user_rev`` would win on pull).
    """
    await _get_or_create_user_revision(db, user_id=user_id)
    tag_ids = [tag.id for tag in await list_tags_for_entry(db, user_id=user_id, entry_id=entry.id)]
    symptoms = _symptoms_map(await list_symptoms_for_entry(db, user_id=user_id, entry_id=entry.id))
    entity_updated_at = (
        _ensure_utc(entry.updated_at) if getattr(entry, "updated_at", None) else datetime.now(UTC)
    )
    return await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="entry",
        entity_id=entry.id,
        operation="upsert",
        payload=_entry_payload_from_model(
            entry, tag_ids=tag_ids, symptoms=symptoms, for_revision_log=True
        ),
        entity_updated_at=entity_updated_at,
    )


async def record_tag_revision(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    operation: str,
    tag: Tag | None = None,
    entity_updated_at: datetime | None = None,
) -> int:
    """Append a revision-log row for a tag mutated via the REST API."""
    if operation == "delete":
        payload: dict[str, Any] = {}
        ts = entity_updated_at or datetime.now(UTC)
    else:
        if tag is None:
            raise ValueError("tag is required for upsert revisions")
        payload = _tag_payload_from_model(tag)
        ts = entity_updated_at or getattr(tag, "updated_at", None) or datetime.now(UTC)
    return await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="tag",
        entity_id=tag_id,
        operation=operation,
        payload=payload,
        entity_updated_at=_ensure_utc(ts),
    )


async def record_symptom_revision(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    symptom_id: uuid.UUID,
    operation: str,
    symptom: Symptom | None = None,
    entity_updated_at: datetime | None = None,
) -> int:
    """Append a revision-log row for a symptom mutated via the REST API."""
    if operation == "delete":
        payload: dict[str, Any] = {}
        ts = entity_updated_at or datetime.now(UTC)
    else:
        if symptom is None:
            raise ValueError("symptom is required for upsert revisions")
        payload = _symptom_payload_from_model(symptom)
        ts = entity_updated_at or getattr(symptom, "updated_at", None) or datetime.now(UTC)
    return await _append_revision_log(
        db,
        user_id=user_id,
        entity_type="symptom",
        entity_id=symptom_id,
        operation=operation,
        payload=payload,
        entity_updated_at=_ensure_utc(ts),
    )


async def ensure_revision_log_backfill(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    """Hydrate ``sync_revision_log`` from online-created entities missing from the log.

    Called on the first pull (``since is None``) so preexisting entries/tags/symptoms
    created via the REST API become visible to offline clients.
    """
    now = datetime.now(UTC)
    threshold = now - timedelta(days=settings.SYNC_INITIAL_PULL_DAYS)

    logged_result = await db.execute(
        select(SyncRevisionLog.entity_id).where(
            SyncRevisionLog.user_id == user_id,
            SyncRevisionLog.operation == "upsert",
        )
    )
    logged_ids = {row[0] for row in logged_result.all()}

    written = 0

    entries_result = await db.execute(
        select(Entry)
        .where(
            Entry.user_id == user_id,
            Entry.updated_at >= threshold,
        )
        .order_by(Entry.updated_at.asc())
    )
    for entry in entries_result.scalars().all():
        if entry.id in logged_ids:
            continue
        tag_ids = [
            tag.id for tag in await list_tags_for_entry(db, user_id=user_id, entry_id=entry.id)
        ]
        symptoms = _symptoms_map(
            await list_symptoms_for_entry(db, user_id=user_id, entry_id=entry.id)
        )
        await _append_revision_log(
            db,
            user_id=user_id,
            entity_type="entry",
            entity_id=entry.id,
            operation="upsert",
            payload=_entry_payload_from_model(
                entry, tag_ids=tag_ids, symptoms=symptoms, for_revision_log=True
            ),
            entity_updated_at=_ensure_utc(entry.updated_at),
        )
        written += 1

    tags_result = await db.execute(
        select(Tag)
        .where(
            Tag.user_id == user_id,
            Tag.is_default.is_(False),
            Tag.updated_at >= threshold,
        )
        .order_by(Tag.updated_at.asc())
    )
    for tag in tags_result.scalars().all():
        if tag.id in logged_ids:
            continue
        await _append_revision_log(
            db,
            user_id=user_id,
            entity_type="tag",
            entity_id=tag.id,
            operation="upsert",
            payload=_tag_payload_from_model(tag),
            entity_updated_at=_ensure_utc(tag.updated_at),
        )
        written += 1

    symptoms_result = await db.execute(
        select(Symptom)
        .where(
            Symptom.user_id == user_id,
            Symptom.is_default.is_(False),
            Symptom.updated_at >= threshold,
        )
        .order_by(Symptom.updated_at.asc())
    )
    for symptom in symptoms_result.scalars().all():
        if symptom.id in logged_ids:
            continue
        await _append_revision_log(
            db,
            user_id=user_id,
            entity_type="symptom",
            entity_id=symptom.id,
            operation="upsert",
            payload=_symptom_payload_from_model(symptom),
            entity_updated_at=_ensure_utc(symptom.updated_at),
        )
        written += 1

    if written:
        logger.info(
            "sync.pull.backfill",
            extra={"user_id": str(user_id), "written": written},
        )
    return written


async def pull_changes(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    since: str | None,
    limit: int = DEFAULT_PULL_LIMIT,
) -> SyncPullResponse:
    limit = max(1, min(limit, MAX_PULL_LIMIT))
    now = datetime.now(UTC)

    if not since:
        await ensure_revision_log_backfill(db, user_id=user_id)

    stmt = select(SyncRevisionLog).where(SyncRevisionLog.user_id == user_id)
    if since:
        min_rev, _wall = decode_cursor(since)
        stmt = stmt.where(SyncRevisionLog.user_rev > min_rev)
    else:
        threshold = now - timedelta(days=settings.SYNC_INITIAL_PULL_DAYS)
        stmt = stmt.where(SyncRevisionLog.created_at >= threshold)

    stmt = stmt.order_by(SyncRevisionLog.user_rev.asc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    page = rows[:limit]

    revision = await _get_or_create_user_revision(db, user_id=user_id)
    cursor_rev = page[-1].user_rev if page else int(revision.current_rev)
    changes: list[SyncChange] = []
    for row in page:
        changes.append(await _revision_to_pull_change(db, user_id=user_id, row=row))
    response = SyncPullResponse(
        cursor=encode_cursor(user_rev=cursor_rev, wall=now),
        changes=changes,
        has_more=has_more,
        server_time=now,
    )

    logger.info(
        "sync.pull.completed",
        extra={
            "user_id": str(user_id),
            "change_count": len(page),
            "has_more": has_more,
        },
    )
    return response
