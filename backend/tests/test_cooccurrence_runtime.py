from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.core.config import settings
from app.services.cooccurrence_runtime import (
    CooccurrenceBusyError,
    CooccurrenceRunner,
    CooccurrenceTimeoutError,
    CooccurrenceWorkerError,
    compute_tag_tag_job,
    plan_symptom_tag_work,
    plan_tag_tag_work,
    work_limit_reason,
)
from app.services.symptom_analytics import (
    CooccurrenceComputationTimeout,
    DailySymptomEntry,
    SymptomRef,
    TagRef,
    _cooccurrence_stats,
    _cooccurrence_stats_from_presence,
)


def _sleep_and_return(delay: float, value: str) -> str:
    time.sleep(delay)
    return value


def _raise_worker_error() -> None:
    raise ValueError("worker failed")


class _BrokenExecutor:
    def submit(self, *args, **kwargs):
        raise BrokenProcessPool("broken")

    def shutdown(self, *args, **kwargs) -> None:
        return None


def _entries(*, days: int, tag_ids: list, symptom_ids: list) -> list[DailySymptomEntry]:
    start = date(2026, 1, 1)
    return [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=3,
            energy=3,
            stress=3,
            tag_ids=frozenset(tag_ids),
            symptom_ids=frozenset(symptom_ids),
        )
        for offset in range(days)
    ]


def test_work_plans_count_the_complete_fdr_family_before_computation() -> None:
    tag_ids = [uuid4() for _ in range(4)]
    symptom_ids = [uuid4() for _ in range(3)]
    entries = _entries(days=60, tag_ids=tag_ids, symptom_ids=symptom_ids)
    tags = {value: TagRef(id=value, label=str(value), slug=str(value)) for value in tag_ids}
    symptoms = {
        value: SymptomRef(id=value, label=str(value), slug=str(value)) for value in symptom_ids
    }

    tag_plan = plan_tag_tag_work(entries, tags, min_tag_usages=5)
    symptom_plan = plan_symptom_tag_work(
        entries,
        symptoms,
        tags,
        min_symptom_usages=5,
        min_tag_usages=5,
    )

    assert (tag_plan.pair_count, tag_plan.work_units) == (6, 360)
    assert (symptom_plan.pair_count, symptom_plan.work_units) == (12, 720)
    assert work_limit_reason(tag_plan) is None


def test_work_plan_returns_typed_limit_without_truncating_pairs(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COOCCURRENCE_MAX_PAIRS", 5)
    tag_ids = [uuid4() for _ in range(4)]
    tags = {value: TagRef(id=value, label=str(value), slug=str(value)) for value in tag_ids}
    plan = plan_tag_tag_work(_entries(days=60, tag_ids=tag_ids, symptom_ids=[]), tags, min_tag_usages=5)

    assert plan.pair_count == 6
    assert work_limit_reason(plan) == "pair_count"


def test_work_plan_rejects_excess_supplied_signals_even_when_unused(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COOCCURRENCE_MAX_SUPPLIED_TAGS", 3)
    tag_ids = [uuid4() for _ in range(4)]
    tags = {value: TagRef(id=value, label=str(value), slug=str(value)) for value in tag_ids}
    plan = plan_tag_tag_work([], tags, min_tag_usages=5)

    assert plan.eligible_tags == 0
    assert work_limit_reason(plan) == "supplied_tags"


def test_precomputed_pair_counts_are_statistically_equivalent() -> None:
    tag_ids = [uuid4(), uuid4()]
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=3,
            energy=3,
            stress=3,
            tag_ids=frozenset(
                tag_id
                for index, tag_id in enumerate(tag_ids)
                if (offset + index * 2) % 5 < 3
            ),
            symptom_ids=frozenset(),
        )
        for offset in range(30)
    ]
    legacy = _cooccurrence_stats(
        entries,
        signal_a_id=tag_ids[0],
        signal_b_id=tag_ids[1],
        kind_a="tag",
        kind_b="tag",
    )
    optimized = _cooccurrence_stats_from_presence(
        frozenset(index for index, entry in enumerate(entries) if tag_ids[0] in entry.tag_ids),
        frozenset(index for index, entry in enumerate(entries) if tag_ids[1] in entry.tag_ids),
        total=len(entries),
    )

    assert optimized == pytest.approx(legacy)


@pytest.mark.asyncio
async def test_runner_deduplicates_and_caches_exact_requests(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COOCCURRENCE_PROCESS_WORKERS", 1)
    monkeypatch.setattr(settings, "COOCCURRENCE_MAX_QUEUE_SIZE", 1)
    monkeypatch.setattr(settings, "COOCCURRENCE_JOB_TIMEOUT_SECONDS", 1.0)
    runner = CooccurrenceRunner()
    runner._executor = ThreadPoolExecutor(max_workers=1)  # type: ignore[assignment]
    user_id = uuid4()
    try:
        first, duplicate = await asyncio.gather(
            runner.run(
                key=(user_id, "same-data"),
                user_id=user_id,
                function=_sleep_and_return,
                args=(0.03, "ok"),
            ),
            runner.run(
                key=(user_id, "same-data"),
                user_id=user_id,
                function=_sleep_and_return,
                args=(0.03, "ok"),
            ),
        )
        cached = await runner.run(
            key=(user_id, "same-data"),
            user_id=user_id,
            function=_raise_worker_error,
            args=(),
        )
    finally:
        runner.shutdown()

    assert (first, duplicate, cached) == ("ok", "ok", "ok")


@pytest.mark.asyncio
async def test_cache_keys_remain_isolated_by_user(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COOCCURRENCE_JOB_TIMEOUT_SECONDS", 1.0)
    runner = CooccurrenceRunner()
    runner._executor = ThreadPoolExecutor(max_workers=1)  # type: ignore[assignment]
    user_a = uuid4()
    user_b = uuid4()
    try:
        value_a = await runner.run(
            key=(user_a, "same-window", "same-data"),
            user_id=user_a,
            function=_sleep_and_return,
            args=(0.0, "user-a"),
        )
        value_b = await runner.run(
            key=(user_b, "same-window", "same-data"),
            user_id=user_b,
            function=_sleep_and_return,
            args=(0.0, "user-b"),
        )
    finally:
        runner.shutdown()

    assert (value_a, value_b) == ("user-a", "user-b")


@pytest.mark.asyncio
async def test_runner_bounds_per_user_and_global_queue(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COOCCURRENCE_PROCESS_WORKERS", 1)
    monkeypatch.setattr(settings, "COOCCURRENCE_MAX_QUEUE_SIZE", 0)
    monkeypatch.setattr(settings, "COOCCURRENCE_JOB_TIMEOUT_SECONDS", 1.0)
    runner = CooccurrenceRunner()
    runner._executor = ThreadPoolExecutor(max_workers=1)  # type: ignore[assignment]
    user_id = uuid4()
    admitted = asyncio.create_task(
        runner.run(
            key=(user_id, "first"),
            user_id=user_id,
            function=_sleep_and_return,
            args=(0.08, "ok"),
        )
    )
    await asyncio.sleep(0.01)
    try:
        with pytest.raises(CooccurrenceBusyError):
            await runner.run(
                key=(user_id, "second"),
                user_id=user_id,
                function=_sleep_and_return,
                args=(0.01, "no"),
            )
        with pytest.raises(CooccurrenceBusyError):
            await runner.run(
                key=(uuid4(), "queue-full"),
                user_id=uuid4(),
                function=_sleep_and_return,
                args=(0.01, "no"),
            )
        assert await admitted == "ok"
    finally:
        runner.shutdown()


@pytest.mark.asyncio
async def test_runner_maps_timeout_and_worker_failure(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COOCCURRENCE_PROCESS_WORKERS", 1)
    monkeypatch.setattr(settings, "COOCCURRENCE_MAX_QUEUE_SIZE", 1)
    monkeypatch.setattr(settings, "COOCCURRENCE_JOB_TIMEOUT_SECONDS", 0.01)
    runner = CooccurrenceRunner()
    runner._executor = ThreadPoolExecutor(max_workers=1)  # type: ignore[assignment]
    timed_out_user = uuid4()
    try:
        with pytest.raises(CooccurrenceTimeoutError):
            await runner.run(
                key=(uuid4(), "slow"),
                user_id=timed_out_user,
                function=_sleep_and_return,
                args=(0.1, "late"),
            )
        with pytest.raises(CooccurrenceBusyError):
            await runner.run(
                key=(timed_out_user, "too-soon"),
                user_id=timed_out_user,
                function=_sleep_and_return,
                args=(0.0, "no"),
            )
        await asyncio.sleep(0.11)
        monkeypatch.setattr(settings, "COOCCURRENCE_JOB_TIMEOUT_SECONDS", 1.0)
        with pytest.raises(CooccurrenceWorkerError):
            await runner.run(
                key=(uuid4(), "broken"),
                user_id=uuid4(),
                function=_raise_worker_error,
                args=(),
            )
    finally:
        runner.shutdown()


@pytest.mark.asyncio
async def test_runner_discards_broken_pool_for_restart(monkeypatch) -> None:
    monkeypatch.setattr(settings, "COOCCURRENCE_JOB_TIMEOUT_SECONDS", 1.0)
    runner = CooccurrenceRunner()
    runner._executor = _BrokenExecutor()  # type: ignore[assignment]

    with pytest.raises(CooccurrenceWorkerError):
        await runner.run(
            key=(uuid4(), "broken-pool"),
            user_id=uuid4(),
            function=_sleep_and_return,
            args=(0.0, "never"),
        )

    assert runner._executor is None


def test_compute_job_enforces_its_own_deadline_after_http_timeout() -> None:
    tag_ids = [uuid4(), uuid4()]
    tags = {value: TagRef(id=value, label=str(value), slug=str(value)) for value in tag_ids}
    entries = _entries(days=20, tag_ids=tag_ids, symptom_ids=[])

    with pytest.raises(CooccurrenceComputationTimeout):
        compute_tag_tag_job(entries, tags, 5, -1.0)
