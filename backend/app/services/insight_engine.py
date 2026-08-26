"""M3 analytics insight engine — orchestration and persistence.

This module is the public entry point for insight generation. The statistical
insight families were extracted into :mod:`app.services.insights` (#777); what
remains here is the thin orchestrator (:func:`generate_insight_candidates`), the
per-user generation lock, the DB loaders, and the persistence path
(:func:`generate_and_store_insights`).

The family functions and shared data structures are re-exported below so
existing imports of ``app.services.insight_engine`` keep working unchanged. It
deliberately stays inside the service layer: no API route, scheduler changes or
UI assumptions are introduced here.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from datetime import date as date_type

from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.core.config import settings
from app.core.crypto import DecryptionError
from app.models.entry import Entry
from app.models.entry_note import EntryNoteMarker
from app.models.insight import Insight, InsightTier
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag
from app.services.insights.changepoint import _changepoint_candidates
from app.services.insights.correlation import (
    _pointbiserial_candidates,
    _sleep_spearman_candidates,
    _spearman_candidates,
)
from app.services.insights.multivariate import _lag_candidates, _lasso_candidates
from app.services.insights.shared import (
    MIN_WEEKDAY_ENTRIES,
    AnalyticsEntry,
    InsightCandidate,
    SymptomSnapshot,
    TagSnapshot,
    _canonicalize_tag_aliases,
    _dedupe_daily_entries,
    confidence_tier_for_sample,
    display_metric_value,
    is_weekday_biased,
    is_work_context_biased,
)
from app.services.insights.symptoms import (
    _symptom_metric_candidates,
    _symptom_tag_candidates,
)
from app.services.insights.weekday import (
    _weekday_candidates,
    _weekday_context_candidates,
    _work_context_candidates,
)
from app.services.note_marker_insights import EntryWithMarkers
from app.services.tag_service import analytics_tag_predicate

logger = logging.getLogger(__name__)

# Re-exported names kept for backwards compatibility after the #777 split.
# ``generate_insight_candidates`` (below) composes the family functions above.
__all__ = [
    "AnalyticsEntry",
    "InsightCandidate",
    "InsightLockTimeoutError",
    "MIN_WEEKDAY_ENTRIES",
    "SymptomSnapshot",
    "TagSnapshot",
    "confidence_tier_for_sample",
    "display_metric_value",
    "generate_and_store_insights",
    "generate_insight_candidates",
    "is_weekday_biased",
    "is_work_context_biased",
    "load_analytics_data",
]

# Stable namespace for pg_advisory_xact_lock(int4, int4). Keeps insight-gen
# locks out of the way of unrelated advisory locks in the same database.
_INSIGHT_GENERATION_LOCK_NS = 0x43495247  # 'CIRG' — CorrelCore Insight ReGen


def _insight_generation_lock_keys(user_id: uuid.UUID) -> tuple[int, int]:
    """Return a stable (namespace, key) pair for per-user insight regeneration.

    Two concurrent ``generate_and_store_insights`` transactions for the same
    user must not interleave delete-then-insert: without serialization the
    slower writer can wipe fresher rows (post-batch / worker / regenerate
    overlap) or both can insert duplicate sets when no prior rows exist.
    """

    digest = hashlib.blake2b(user_id.bytes, digest_size=4).digest()
    # signed int4 as required by PostgreSQL's two-argument advisory lock
    key = int.from_bytes(digest, "big", signed=True)
    return _INSIGHT_GENERATION_LOCK_NS, key


class InsightLockTimeoutError(Exception):
    """Raised when the per-user insight-generation lock cannot be acquired.

    #753 (Option H): the previous implementation used the blocking
    ``pg_advisory_xact_lock``, which waits indefinitely for a conflicting
    transaction (scheduled run, manual regenerate, post-batch hook) and
    holds a pooled DB connection the entire time. A bounded, fast-failing
    error lets callers retry later or surface a clear message instead of
    silently starving the connection pool.
    """


async def _generate_insight_candidates_in_thread(
    entries: list[AnalyticsEntry],
    tags: list[TagSnapshot],
    symptoms: list[SymptomSnapshot],
    *,
    as_of: date_type,
) -> list[InsightCandidate]:
    """Run pure, potentially expensive statistics outside the event loop.

    The inputs are fully materialized plain data structures, so no SQLAlchemy
    session or ORM object crosses the thread boundary. ``asyncio.to_thread``
    cannot forcibly stop a running calculation, but it keeps the event loop
    responsive: the worker deadline can proceed with the next user while the
    executor worker winds down.
    """

    return await asyncio.to_thread(
        generate_insight_candidates,
        entries,
        tags,
        symptoms,
        as_of=as_of,
    )


async def _acquire_insight_generation_lock(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Serialize insight regenerate/delete/insert for ``user_id`` until commit.

    Uses ``pg_try_advisory_xact_lock`` (non-blocking) in a bounded retry loop
    with backoff instead of the blocking ``pg_advisory_xact_lock`` — see
    :class:`InsightLockTimeoutError`.
    """

    ns, key = _insight_generation_lock_keys(user_id)
    max_attempts = settings.INSIGHT_LOCK_MAX_ATTEMPTS
    backoff = settings.INSIGHT_LOCK_RETRY_BACKOFF_SECONDS
    for attempt in range(1, max_attempts + 1):
        result = await db.execute(
            text("SELECT pg_try_advisory_xact_lock(:ns, :key)"),
            {"ns": ns, "key": key},
        )
        if result.scalar():
            return
        if attempt < max_attempts:
            await asyncio.sleep(backoff * attempt)

    raise InsightLockTimeoutError(
        f"Could not acquire insight-generation lock for user {user_id} "
        f"after {max_attempts} attempts"
    )


def generate_insight_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot] = (),
    symptoms: Iterable[SymptomSnapshot] = (),
    *,
    as_of: date_type | None = None,
) -> list[InsightCandidate]:
    """Generate deterministic insight candidates from user-owned data."""

    daily_entries = _dedupe_daily_entries(entries)
    if not daily_entries:
        return []

    generated_for_date = as_of or daily_entries[-1].entry_date
    tier = confidence_tier_for_sample(len(daily_entries))
    if tier is InsightTier.NONE:
        return []

    daily_entries, canonical_tags = _canonicalize_tag_aliases(daily_entries, tags)
    tags_by_id = {tag.id: tag for tag in canonical_tags}
    symptom_list = sorted(symptoms, key=lambda symptom: symptom.slug)
    candidates = [
        *_weekday_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_work_context_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_weekday_context_candidates(
            daily_entries,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_spearman_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_sleep_spearman_candidates(daily_entries, generated_for_date=generated_for_date),
        *_pointbiserial_candidates(
            daily_entries,
            tags_by_id,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_symptom_metric_candidates(
            daily_entries,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_symptom_tag_candidates(
            daily_entries,
            canonical_tags,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_lasso_candidates(
            daily_entries,
            canonical_tags,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_lag_candidates(
            daily_entries,
            canonical_tags,
            symptom_list,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
        *_changepoint_candidates(
            daily_entries,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
    ]
    return sorted(
        candidates,
        key=lambda candidate: (
            -(candidate.confidence or 0),
            -abs(candidate.effect_size or 0),
            candidate.insight_type.value,
            candidate.metric,
            candidate.subject_label or "",
        ),
    )


async def _load_analytics_inputs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
) -> tuple[list[AnalyticsEntry], list[TagSnapshot], list[SymptomSnapshot]]:
    result = await db.execute(
        # #758 (M) / #772 review: defer ``note_enc`` so the encrypted note is
        # never loaded here. Its ``EncryptedString`` result processor decrypts
        # eagerly during row materialization (``.all()``), i.e. *before* the
        # per-entry guard below — so an undecryptable note would otherwise abort
        # the whole user's run at load time. Analytics never reads the note, so
        # deferring it removes that failure mode entirely (and skips needless
        # decryption); the per-entry guard still covers residual materialization
        # errors on the columns we do use.
        select(Entry)
        .options(defer(Entry.note_enc))
        # Temporal integrity guard: analytics must follow entry_date only.
        # created_at/updated_at would leak look-ahead bias for backdated entries.
        .where(Entry.user_id == user_id, Entry.entry_date < as_of)
        .order_by(Entry.entry_date.asc(), Entry.slot.asc())
    )
    entries = list(result.scalars().all())
    if not entries:
        return [], [], []

    tag_rows = await db.execute(
        select(EntryTag.entry_id, Tag)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .join(Entry, Entry.id == EntryTag.entry_id)
        .where(
            EntryTag.user_id == user_id,
            Entry.user_id == user_id,
            Entry.entry_date < as_of,
            analytics_tag_predicate(user_id),
        )
    )
    tag_ids_by_entry: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    tags_by_id: dict[uuid.UUID, TagSnapshot] = {}
    for entry_id, tag in tag_rows.all():
        tag_ids_by_entry[entry_id].add(tag.id)
        tags_by_id[tag.id] = TagSnapshot(
            id=tag.id,
            label=tag.name,
            slug=tag.slug,
            is_default=tag.is_default,
        )

    symptom_rows = await db.execute(
        select(EntrySymptom.entry_id, Symptom)
        .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
        .join(Entry, Entry.id == EntrySymptom.entry_id)
        .where(
            EntrySymptom.user_id == user_id,
            EntrySymptom.intensity > 0,
            Entry.user_id == user_id,
            Entry.entry_date < as_of,
            or_(Symptom.is_default.is_(True), Symptom.user_id == user_id),
        )
    )
    symptom_ids_by_entry: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    symptoms_by_id: dict[uuid.UUID, SymptomSnapshot] = {}
    for entry_id, symptom in symptom_rows.all():
        symptom_ids_by_entry[entry_id].add(symptom.id)
        symptoms_by_id[symptom.id] = SymptomSnapshot(
            id=symptom.id,
            label=symptom.display_name,
            slug=symptom.slug,
            is_default=symptom.is_default,
        )

    # #758 (M) Graceful degradation: a single corrupt or undecryptable entry
    # (e.g. a bad enum value or a value that fails to materialize) must be
    # logged and skipped, not abort the whole day's computation for the user.
    # Materializing each AnalyticsEntry in isolation keeps one poisoned row from
    # sinking every insight the user would otherwise still get.
    analytics_entries: list[AnalyticsEntry] = []
    skipped = 0
    for entry in entries:
        try:
            analytics_entries.append(
                AnalyticsEntry(
                    id=entry.id,
                    entry_date=entry.entry_date,
                    mood_score=entry.mood_score,
                    energy=entry.energy,
                    stress=entry.stress,
                    work_context=entry.work_context,
                    tag_ids=frozenset(tag_ids_by_entry.get(entry.id, set())),
                    symptom_ids=frozenset(symptom_ids_by_entry.get(entry.id, set())),
                    sleep_minutes=entry.sleep_minutes,
                    sleep_quality=entry.sleep_quality,
                )
            )
        except (ValueError, TypeError, LookupError, DecryptionError) as exc:
            # Narrow to the errors a corrupt/undecryptable row actually raises
            # (bad enum -> LookupError/ValueError, wrong type -> TypeError,
            # bad ciphertext -> DecryptionError) so an unexpected programming
            # bug still fails the user's job loudly instead of silently
            # shrinking the sample (cursor[bot] review, #772).
            skipped += 1
            logger.warning(
                "skipping unreadable analytics entry",
                extra={"user_id": str(user_id), "entry_id": str(entry.id), "error": str(exc)},
            )
    if skipped:
        logger.warning(
            "analytics input load skipped corrupt entries",
            extra={
                "user_id": str(user_id),
                "skipped_entries": skipped,
                "loaded_entries": len(analytics_entries),
            },
        )
    if not analytics_entries:
        return [], [], []
    canonical_entries, canonical_tags = _canonicalize_tag_aliases(
        analytics_entries,
        tags_by_id.values(),
    )
    return (
        canonical_entries,
        canonical_tags,
        sorted(symptoms_by_id.values(), key=lambda item: item.slug),
    )


def _has_stored_note(*, has_note_enc: object, summary: str | None) -> bool:
    """Presence of a note without decrypting ``Entry.note_enc``.

    ``has_note_enc`` is the SQL ``note_enc IS NOT NULL`` flag (ciphertext
    existence). The summary column is plaintext. Together they match
    :func:`app.services.note_markers.entry_has_note` without triggering
    ``EncryptedString.process_result_value``.
    """

    return bool(has_note_enc) or bool(summary and str(summary).strip())


async def _load_entries_with_markers(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
) -> list[EntryWithMarkers]:
    from app.models.entry import NoteVisibility

    # Same #772 P1 as ``_load_analytics_inputs``: ``EncryptedString`` decrypts
    # ``note_enc`` during ``.all()``, *before* any per-row guard. This loader
    # always runs from ``generate_and_store_insights`` after the analytics
    # load, so deferring only there left one undecryptable note able to abort
    # the whole user job. Select a SQL NULL-check instead of the ciphertext,
    # and never call ``entry_has_note`` (it reads ``note_enc`` and would
    # lazy-load the deferred column).
    has_note_enc = Entry.note_enc.isnot(None).label("has_note_enc")
    entry_rows = await db.execute(
        select(Entry, has_note_enc)
        .options(defer(Entry.note_enc))
        .where(
            Entry.user_id == user_id,
            Entry.entry_date < as_of,
            Entry.note_visibility != NoteVisibility.HIDDEN.value,
        )
    )
    rows = list(entry_rows.all())
    if not rows:
        return []

    marker_rows = await db.execute(
        select(EntryNoteMarker).where(
            EntryNoteMarker.user_id == user_id,
            EntryNoteMarker.entry_id.in_([entry.id for entry, _has_note in rows]),
        )
    )
    markers_by_entry: dict[uuid.UUID, set[str]] = defaultdict(set)
    for marker in marker_rows.scalars().all():
        markers_by_entry[marker.entry_id].add(marker.marker)

    loaded: list[EntryWithMarkers] = []
    skipped = 0
    for entry, has_note_enc_flag in rows:
        try:
            loaded.append(
                EntryWithMarkers(
                    entry_id=entry.id,
                    entry_date=entry.entry_date,
                    mood_score=entry.mood_score,
                    markers=frozenset(markers_by_entry.get(entry.id, set())),
                    has_note=_has_stored_note(
                        has_note_enc=has_note_enc_flag,
                        summary=entry.note_summary_short,
                    ),
                )
            )
        except (ValueError, TypeError, LookupError, DecryptionError) as exc:
            skipped += 1
            logger.warning(
                "skipping unreadable marker entry",
                extra={"user_id": str(user_id), "entry_id": str(entry.id), "error": str(exc)},
            )
    if skipped:
        logger.warning(
            "marker input load skipped corrupt entries",
            extra={
                "user_id": str(user_id),
                "skipped_entries": skipped,
                "loaded_entries": len(loaded),
            },
        )
    return loaded


async def load_analytics_data(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
) -> tuple[list[AnalyticsEntry], list[TagSnapshot], list[SymptomSnapshot]]:
    """Load sanitized analytics rows for tests and diagnostics.

    The public wrapper preserves the M3 service contract while keeping the
    query implementation private to this module.
    """

    return await _load_analytics_inputs(db, user_id=user_id, as_of=as_of)


async def generate_and_store_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
) -> list[Insight]:
    """Regenerate and store M3 insight rows for a user/date.

    Idempotent for ``(user_id, generated_for_date)``: only rows for that
    calendar day are replaced. Insights from earlier ``generated_for_date``
    values are retained until account deletion (CASCADE) so the history /
    timeline surface (#601 Phase 2) can show pattern evolution.

    The caller must bind the user's DEK before flushing because
    ``Insight.statement_enc`` uses :class:`app.core.crypto.EncryptedString`.

    A per-user transaction advisory lock is taken **before** loading inputs so
    overlapping regenerate / post-batch / analytics-worker runs cannot
    interleave: a slower transaction that loaded stale data must not delete
    fresher committed rows, and two empty-table writers must not both insert.
    The lock is released automatically on commit/rollback.
    """

    # Lock before load+compute so waiters re-read after the winner commits.
    await _acquire_insight_generation_lock(db, user_id=user_id)

    generated_for_date = as_of or datetime.now(UTC).date()
    entries, tags, symptoms = await _load_analytics_inputs(
        db,
        user_id=user_id,
        as_of=generated_for_date,
    )
    candidates = await _generate_insight_candidates_in_thread(
        entries,
        tags,
        symptoms,
        as_of=generated_for_date,
    )
    from app.services.note_marker_insights import build_marker_mood_insights

    marker_rows = await _load_entries_with_markers(db, user_id=user_id, as_of=generated_for_date)
    candidates.extend(
        await asyncio.to_thread(
            build_marker_mood_insights,
            marker_rows,
            generated_for_date=generated_for_date,
        )
    )

    if settings.INSIGHTS_LLM_ENABLED:
        from app.services.llm_statements import generate_llm_statement

        enhanced: list[InsightCandidate] = []
        for candidate in candidates:
            llm_statement = await generate_llm_statement(
                {
                    "insight_type": candidate.insight_type.value,
                    "metric": candidate.metric,
                    "effect_size": candidate.effect_size,
                    "statement": candidate.statement,
                },
                locale="en",
            )
            if llm_statement:
                enhanced.append(
                    InsightCandidate(
                        insight_type=candidate.insight_type,
                        tier=candidate.tier,
                        metric=candidate.metric,
                        subject_type=candidate.subject_type,
                        subject_id=candidate.subject_id,
                        subject_label=candidate.subject_label,
                        effect_size=candidate.effect_size,
                        confidence=candidate.confidence,
                        sample_n=candidate.sample_n,
                        statement=llm_statement,
                        flags=candidate.flags,
                        payload=candidate.payload,
                        generated_for_date=candidate.generated_for_date,
                    )
                )
            else:
                enhanced.append(candidate)
        candidates = enhanced

    await db.execute(
        delete(Insight).where(
            Insight.user_id == user_id,
            Insight.generated_for_date == generated_for_date,
        )
    )

    insights = [
        Insight(
            user_id=user_id,
            insight_type=candidate.insight_type,
            tier=candidate.tier,
            metric=candidate.metric,
            subject_type=candidate.subject_type,
            subject_id=candidate.subject_id,
            subject_label=candidate.subject_label,
            effect_size=candidate.effect_size,
            confidence=candidate.confidence,
            sample_n=candidate.sample_n,
            statement_enc=candidate.statement,
            flags=candidate.flags,
            payload=candidate.payload,
            generated_for_date=candidate.generated_for_date,
        )
        for candidate in candidates
    ]
    for insight in insights:
        db.add(insight)
    await db.flush()
    logger.info(
        "insights.generated",
        extra={"user_id": str(user_id), "insight_count": len(insights)},
    )
    return insights
