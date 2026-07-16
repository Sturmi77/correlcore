"""Deterministic M7 QA dataset seeding for local full-stack validation.

Bypasses the 7-day API backdate window by inserting rows directly. Intended
only for development and QA — never run against production tenants.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import generate_dek, wrap_dek
from app.db.session import bind_rls_current_user
from app.models.entry import Entry, EntrySlot, EntrySource, WorkContext
from app.models.insight import Insight, InsightType
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user
from app.services.insight_worker_service import InsightGenerationJob, generate_insights_for_job
from app.services.multivariate_analytics import MIN_ML_ENTRIES

logger = logging.getLogger(__name__)

M7_QA_DEFAULT_EMAIL = "m7-qa@localhost.dev"
# Must satisfy RegisterRequest password policy (min 12 + letter + digit).
M7_QA_DEFAULT_PASSWORD = "CorrectHorse123!"
M7_QA_DEFAULT_DISPLAY_NAME = "M7 QA Seed"
M7_QA_DEFAULT_DAYS = 100

# Tag slugs that co-occur often (clustering) and pair with symptoms.
_M7_QA_TAG_SLUGS: tuple[str, ...] = (
    "sport",
    "running",
    "meditation",
    "yoga",
    "alcohol",
    "caffeine_high",
    "family",
    "reading",
)

# Default symptoms used for mood and co-occurrence patterns.
_M7_QA_SYMPTOM_SLUGS: tuple[str, ...] = (
    "headache",
    "fatigue",
    "digestion",
)


@dataclass(frozen=True)
class M7QaDayPlan:
    """One synthetic daily row for the M7 QA seed."""

    entry_date: date
    mood_score: int
    energy: int
    stress: int
    tag_slugs: frozenset[str]
    symptom_slugs: frozenset[str]
    work_context: WorkContext


@dataclass(frozen=True)
class M7QaSeedSummary:
    """Result counters after seeding and analytics recompute."""

    user_id: uuid.UUID
    email: str
    entry_count: int
    insight_count: int
    insight_counts_by_type: dict[str, int]
    has_lasso_or_lag: bool
    has_symptom_insights: bool


def build_m7_qa_day_plans(
    *,
    end_date: date,
    day_count: int = M7_QA_DEFAULT_DAYS,
) -> list[M7QaDayPlan]:
    """Return a deterministic day plan with embedded M7 signal patterns.

    Patterns baked in:
    - Headache every third day lowers mood (symptom_mood_association).
    - Sport on weekdays with fatigue lag on following days (lag analysis).
    - Alcohol co-occurs with headache and low mood (symptom_tag_cooccurrence).
    - Sport/running/yoga cluster together (tag groups).
    """

    if day_count < MIN_ML_ENTRIES:
        msg = f"day_count must be at least {MIN_ML_ENTRIES} for M7 ML gates"
        raise ValueError(msg)

    start_date = end_date - timedelta(days=day_count - 1)
    plans: list[M7QaDayPlan] = []

    for offset in range(day_count):
        entry_date = start_date + timedelta(days=offset)
        weekday = entry_date.weekday()

        headache_day = offset % 3 == 0
        sport_day = weekday < 5 and offset % 2 == 0
        alcohol_day = offset % 7 == 5
        meditation_day = offset % 4 == 1

        tag_slugs: set[str] = set()
        symptom_slugs: set[str] = set()

        if sport_day:
            tag_slugs.add("sport")
            if offset % 4 == 0:
                tag_slugs.add("running")
        if meditation_day:
            tag_slugs.update({"meditation", "yoga"})
        if alcohol_day:
            tag_slugs.add("alcohol")
        if offset % 5 == 2:
            tag_slugs.add("family")
        if offset % 6 == 0:
            tag_slugs.add("reading")

        if headache_day:
            symptom_slugs.add("headache")
        if sport_day and offset % 5 == 1:
            symptom_slugs.add("fatigue")
        if alcohol_day:
            symptom_slugs.add("digestion")

        mood_score = 4
        energy = 4
        stress = 2

        if headache_day:
            mood_score = 2
            energy = 2
            stress = 4
        elif sport_day:
            mood_score = 4
            energy = 5
            stress = 2
        elif alcohol_day:
            mood_score = 2
            energy = 3
            stress = 3

        work_context = WorkContext.HOMEOFFICE
        if weekday >= 5:
            work_context = WorkContext.WEEKEND
        elif sport_day:
            work_context = WorkContext.OFFICE

        plans.append(
            M7QaDayPlan(
                entry_date=entry_date,
                mood_score=mood_score,
                energy=energy,
                stress=stress,
                tag_slugs=frozenset(tag_slugs),
                symptom_slugs=frozenset(symptom_slugs),
                work_context=work_context,
            )
        )

    return plans


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def _load_slug_maps(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> tuple[dict[str, Tag], dict[str, Symptom]]:
    tag_result = await db.execute(
        select(Tag).where(
            Tag.is_default.is_(True),
            Tag.slug.in_(_M7_QA_TAG_SLUGS),
        )
    )
    tags_by_slug = {tag.slug: tag for tag in tag_result.scalars().all()}

    symptom_result = await db.execute(
        select(Symptom).where(
            Symptom.is_default.is_(True),
            Symptom.slug.in_(_M7_QA_SYMPTOM_SLUGS),
        )
    )
    symptoms_by_slug = {symptom.slug: symptom for symptom in symptom_result.scalars().all()}

    missing_tags = set(_M7_QA_TAG_SLUGS) - set(tags_by_slug)
    missing_symptoms = set(_M7_QA_SYMPTOM_SLUGS) - set(symptoms_by_slug)
    if missing_tags or missing_symptoms:
        msg = (
            "M7 QA seed requires default tags and symptoms; "
            f"missing tags={sorted(missing_tags)} symptoms={sorted(missing_symptoms)}"
        )
        raise RuntimeError(msg)

    await bind_rls_current_user(db, user_id)
    return tags_by_slug, symptoms_by_slug


async def _clear_user_analytics_data(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    await bind_rls_current_user(db, user_id)
    await db.execute(delete(Insight).where(Insight.user_id == user_id))
    await db.execute(text("DELETE FROM tag_vectors WHERE user_id = :user_id"), {"user_id": user_id})
    await db.execute(delete(Entry).where(Entry.user_id == user_id))


async def _ensure_verified_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
) -> tuple[User, bytes]:
    existing = await _get_user_by_email(db, email)
    if existing is not None:
        await bind_rls_current_user(db, existing.id)
        key_result = await db.execute(
            select(UserEncryptionKey.wrapped_dek).where(UserEncryptionKey.user_id == existing.id)
        )
        wrapped_dek = key_result.scalar_one_or_none()
        if wrapped_dek is None:
            dek = generate_dek()
            wrapped_dek = wrap_dek(dek)
            db.add(
                UserEncryptionKey(
                    user_id=existing.id,
                    wrapped_dek=wrapped_dek,
                    key_version=1,
                )
            )
        if not existing.is_verified:
            existing.is_verified = True
        return existing, bytes(wrapped_dek)

    user = await register_user(
        db,
        RegisterRequest(email=email, password=password, display_name=display_name),
    )
    user.is_verified = True
    key_result = await db.execute(
        select(UserEncryptionKey.wrapped_dek).where(UserEncryptionKey.user_id == user.id)
    )
    wrapped_dek = key_result.scalar_one()
    return user, bytes(wrapped_dek)


async def seed_m7_qa_dataset(
    db: AsyncSession,
    *,
    email: str = M7_QA_DEFAULT_EMAIL,
    password: str = M7_QA_DEFAULT_PASSWORD,
    display_name: str = M7_QA_DEFAULT_DISPLAY_NAME,
    day_count: int = M7_QA_DEFAULT_DAYS,
    end_date: date | None = None,
    reset: bool = False,
) -> M7QaSeedSummary:
    """Create or refresh a verified QA user with ``day_count`` analytics-ready entries."""

    as_of = end_date or datetime.now(UTC).date()
    user, wrapped_dek = await _ensure_verified_user(
        db,
        email=email,
        password=password,
        display_name=display_name,
    )

    if reset:
        await _clear_user_analytics_data(db, user_id=user.id)

    tags_by_slug, symptoms_by_slug = await _load_slug_maps(db, user_id=user.id)
    plans = build_m7_qa_day_plans(end_date=as_of, day_count=day_count)

    for plan in plans:
        entry = Entry(
            user_id=user.id,
            entry_date=plan.entry_date,
            slot=EntrySlot.DAY,
            mood_score=plan.mood_score,
            energy=plan.energy,
            stress=plan.stress,
            source=EntrySource.RETROSPECTIVE,
            work_context=plan.work_context,
            note_enc=None,
        )
        db.add(entry)
        await db.flush()

        for slug in plan.tag_slugs:
            db.add(
                EntryTag(
                    entry_id=entry.id,
                    tag_id=tags_by_slug[slug].id,
                    user_id=user.id,
                )
            )
        for slug in plan.symptom_slugs:
            db.add(
                EntrySymptom(
                    entry_id=entry.id,
                    symptom_id=symptoms_by_slug[slug].id,
                    user_id=user.id,
                    intensity=2,
                )
            )

    await db.flush()

    job = InsightGenerationJob(user_id=user.id, wrapped_dek=wrapped_dek)
    await generate_insights_for_job(db, job=job, as_of=as_of)

    count_result = await db.execute(
        select(func.count()).select_from(Entry).where(Entry.user_id == user.id)
    )
    entry_count = int(count_result.scalar_one())

    insight_rows = await db.execute(
        select(Insight.insight_type, func.count())
        .where(Insight.user_id == user.id)
        .group_by(Insight.insight_type)
    )
    insight_counts_by_type = {
        insight_type.value: int(count) for insight_type, count in insight_rows.all()
    }
    insight_count = sum(insight_counts_by_type.values())

    has_lasso_or_lag = insight_counts_by_type.get(InsightType.SYMPTOM_CLUSTER.value, 0) > 0
    has_symptom_insights = any(
        insight_counts_by_type.get(key, 0) > 0
        for key in (
            InsightType.SYMPTOM_MOOD_ASSOCIATION.value,
            InsightType.SYMPTOM_TAG_COOCCURRENCE.value,
        )
    )

    logger.info(
        "m7_qa_seed.completed",
        extra={
            "user_id": str(user.id),
            "email": user.email,
            "entry_count": entry_count,
            "insight_count": insight_count,
        },
    )

    return M7QaSeedSummary(
        user_id=user.id,
        email=user.email,
        entry_count=entry_count,
        insight_count=insight_count,
        insight_counts_by_type=insight_counts_by_type,
        has_lasso_or_lag=has_lasso_or_lag,
        has_symptom_insights=has_symptom_insights,
    )


def format_seed_summary(summary: M7QaSeedSummary) -> str:
    """Human-readable seed result for CLI output."""

    lines = [
        f"M7 QA seed complete for {summary.email} ({summary.user_id})",
        f"  entries: {summary.entry_count}",
        f"  insights: {summary.insight_count}",
        f"  lasso/lag (symptom_cluster): {'yes' if summary.has_lasso_or_lag else 'no'}",
        f"  symptom insights: {'yes' if summary.has_symptom_insights else 'no'}",
    ]
    if summary.insight_counts_by_type:
        lines.append("  by type:")
        for insight_type, count in sorted(summary.insight_counts_by_type.items()):
            lines.append(f"    - {insight_type}: {count}")
    return "\n".join(lines)
