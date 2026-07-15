"""Note signal extraction from free-text entry notes (Notes in Analysis #201)."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.entry import Entry, NoteVisibility
from app.models.entry_note import EntryNoteSignal
from app.models.user_encryption_key import UserEncryptionKey

logger = logging.getLogger(__name__)

EXTRACTOR_V = "v1"
DICTIONARY_CONFIDENCE = 0.90

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

# Dictionary layer — normalized signal keys with German + English triggers.
SIGNAL_DICT: dict[str, tuple[str, ...]] = {
    "konflikt": ("konflikt", "streit", "auseinandersetzung", "argument", "conflict", "fight"),
    "isolation": ("alleine", "niemand", "isoliert", "einsam", "lonely", "alone", "isolated"),
    "spaziergang": ("spazieren", "spaziergang", "walk", "draußen", "draussen", "hiking"),
    "kopfschmerz": ("kopfschmerzen", "migräne", "migrane", "headache", "headaches"),
    "stress": ("stress", "gestresst", "stressed", "überlastet", "ueberlastet", "overwhelmed"),
    "muedigkeit": ("müde", "muede", "tired", "exhausted", "erschöpft", "erschoepft"),
    "schlaf": ("schlaf", "sleep", "insomnia", "schlaflos", "sleepless"),
    "arbeit": ("arbeit", "work", "meeting", "deadline", "büro", "buero", "office"),
    "sozial": ("freunde", "friends", "party", "family", "familie", "social"),
}

# Regex layer — (pattern, signal_key, confidence).
SIGNAL_REGEX: tuple[tuple[re.Pattern[str], str, float], ...] = (
    (re.compile(r"schlecht(?:e[rn]?)?\s+schlaf"), "schlechter_schlaf", 0.80),
    (re.compile(r"bad\s+sleep"), "schlechter_schlaf", 0.80),
    (re.compile(r"gut(?:e[rn]?)?\s+schlaf"), "guter_schlaf", 0.80),
    (re.compile(r"good\s+sleep"), "guter_schlaf", 0.80),
    (re.compile(r"zu\s+viel\s+arbeit"), "arbeit_ueberlast", 0.85),
    (re.compile(r"too\s+much\s+work"), "arbeit_ueberlast", 0.85),
    (re.compile(r"keine?\s+zeit"), "zeitdruck", 0.70),
    (re.compile(r"no\s+time"), "zeitdruck", 0.70),
    (re.compile(r"\bpanik\b"), "angst", 0.75),
    (re.compile(r"\b(anxiety|anxious)\b"), "angst", 0.75),
    (re.compile(r"\b(deprimiert|depressed)\b"), "niedergeschlagen", 0.65),
    (re.compile(r"\d+\s*h(?:ours?)?\b"), "schlafdauer", 0.60),
)


@dataclass(frozen=True)
class ExtractedSignal:
    signal: str
    confidence: float
    source_span: str


def preprocess_note(text: str) -> str:
    """Lowercase and strip HTML tags before rule matching."""

    cleaned = _HTML_TAG.sub(" ", text)
    cleaned = _WHITESPACE.sub(" ", cleaned.strip())
    return cleaned.casefold()


def extract_signals_from_text(text: str | None) -> list[ExtractedSignal]:
    """Run dictionary + regex extraction on preprocessed note text."""

    if not text or not text.strip():
        return []

    normalized = preprocess_note(text)
    if not normalized:
        return []

    found: dict[str, ExtractedSignal] = {}

    for signal_key, terms in SIGNAL_DICT.items():
        for term in terms:
            idx = normalized.find(term.casefold())
            if idx == -1:
                continue
            span = normalized[idx : idx + len(term)]
            existing = found.get(signal_key)
            if existing is None or existing.confidence < DICTIONARY_CONFIDENCE:
                found[signal_key] = ExtractedSignal(
                    signal=signal_key,
                    confidence=DICTIONARY_CONFIDENCE,
                    source_span=span,
                )
            break

    for pattern, signal_key, confidence in SIGNAL_REGEX:
        match = pattern.search(normalized)
        if match is None:
            continue
        span = match.group(0)
        existing = found.get(signal_key)
        if existing is None or existing.confidence < confidence:
            found[signal_key] = ExtractedSignal(
                signal=signal_key,
                confidence=confidence,
                source_span=span,
            )

    return sorted(found.values(), key=lambda item: (-item.confidence, item.signal))


def meets_insight_threshold(confidence: float) -> bool:
    """Return True when a signal qualifies for insight evidence (ADR-N-02)."""

    return confidence >= settings.NOTE_SIGNAL_MIN_CONFIDENCE


def filter_signals_for_insight(signals: Sequence[ExtractedSignal]) -> list[ExtractedSignal]:
    """Filter extracted signals to those meeting the insight confidence gate."""

    return [signal for signal in signals if meets_insight_threshold(signal.confidence)]


async def load_user_dek(db: AsyncSession, *, user_id: uuid.UUID) -> bytes | None:
    result = await db.execute(
        select(UserEncryptionKey.wrapped_dek).where(UserEncryptionKey.user_id == user_id)
    )
    wrapped = result.scalar_one_or_none()
    if wrapped is None:
        return None
    return unwrap_dek(wrapped)


async def extract_and_store_signals_for_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> list[EntryNoteSignal]:
    """Replace stored signals for one entry from its current note content."""

    result = await db.execute(
        select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return []

    await db.execute(
        delete(EntryNoteSignal).where(
            EntryNoteSignal.entry_id == entry_id,
            EntryNoteSignal.user_id == user_id,
        )
    )

    if entry.note_visibility == NoteVisibility.HIDDEN:
        await db.flush()
        return []

    extracted = extract_signals_from_text(entry.note_enc)
    stored: list[EntryNoteSignal] = []
    for item in extracted:
        row = EntryNoteSignal(
            entry_id=entry_id,
            user_id=user_id,
            signal=item.signal,
            confidence=round(item.confidence, 3),
            source_span=item.source_span,
            extractor_v=EXTRACTOR_V,
        )
        db.add(row)
        stored.append(row)

    await db.flush()
    return stored


async def list_signals_for_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> list[EntryNoteSignal]:
    """Return stored signals for one owned entry, highest confidence first."""

    result = await db.execute(
        select(EntryNoteSignal)
        .where(
            EntryNoteSignal.user_id == user_id,
            EntryNoteSignal.entry_id == entry_id,
        )
        .order_by(EntryNoteSignal.confidence.desc(), EntryNoteSignal.signal.asc())
    )
    return list(result.scalars().all())


async def list_signals_for_entries(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, list[EntryNoteSignal]]:
    """Batch-load signals keyed by entry id."""

    if not entry_ids:
        return {}

    result = await db.execute(
        select(EntryNoteSignal)
        .where(
            EntryNoteSignal.user_id == user_id,
            EntryNoteSignal.entry_id.in_(entry_ids),
        )
        .order_by(EntryNoteSignal.confidence.desc(), EntryNoteSignal.signal.asc())
    )
    grouped: dict[uuid.UUID, list[EntryNoteSignal]] = {entry_id: [] for entry_id in entry_ids}
    for row in result.scalars().all():
        grouped[row.entry_id].append(row)
    return grouped


async def run_note_signal_extraction_background(
    *,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Background task entry point — opens its own session and binds the user DEK."""

    async with AsyncSessionLocal() as session:
        dek_token = None
        try:
            await bind_rls_current_user(session, user_id)
            dek = await load_user_dek(session, user_id=user_id)
            if dek is not None:
                dek_token = set_current_user_dek(user_id, dek)
            await extract_and_store_signals_for_entry(
                session,
                user_id=user_id,
                entry_id=entry_id,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "note signal extraction failed",
                extra={"user_id": str(user_id), "entry_id": str(entry_id)},
            )
        finally:
            if dek_token is not None:
                reset_current_user_dek(dek_token)  # type: ignore[arg-type]
