"""Bounded execution for interactive co-occurrence analytics.

The HTTP endpoints must never execute scipy/statsmodels work on the asyncio
event loop.  This module owns the process capacity, queue admission, exact
request de-duplication, and the small in-process result cache.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable, Hashable, Mapping, Sequence
from concurrent.futures import Future as ConcurrentFuture
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from typing import Any, TypeVar

from app.core.config import settings
from app.services.symptom_analytics import (
    CooccurrenceComputationTimeout,
    DailySymptomEntry,
    SymptomRef,
    SymptomTagAssociation,
    TagRef,
    TagTagAssociation,
    heatmap_symptom_tag_associations,
    heatmap_tag_tag_associations,
)

T = TypeVar("T")
COOCCURRENCE_ALGORITHM_VERSION = "fisher-bh-v2"


class CooccurrenceBusyError(RuntimeError):
    """The bounded queue or this user's concurrency slot is occupied."""


class CooccurrenceTimeoutError(RuntimeError):
    """The admitted job exceeded its wall-clock budget."""


class CooccurrenceWorkerError(RuntimeError):
    """The process worker failed before producing a result."""


@dataclass(frozen=True)
class CooccurrenceWorkPlan:
    supplied_tags: int
    supplied_symptoms: int
    eligible_tags: int
    eligible_symptoms: int
    pair_count: int
    work_units: int


def plan_tag_tag_work(
    entries: Sequence[DailySymptomEntry],
    tags: Mapping[uuid.UUID, TagRef],
    *,
    min_tag_usages: int,
) -> CooccurrenceWorkPlan:
    counts = dict.fromkeys(tags, 0)
    for entry in entries:
        for tag_id in entry.tag_ids:
            if tag_id in counts:
                counts[tag_id] += 1
    eligible_tags = sum(count >= min_tag_usages for count in counts.values())
    pair_count = eligible_tags * (eligible_tags - 1) // 2
    return CooccurrenceWorkPlan(
        supplied_tags=len(tags),
        supplied_symptoms=0,
        eligible_tags=eligible_tags,
        eligible_symptoms=0,
        pair_count=pair_count,
        work_units=len(entries) * pair_count,
    )


def plan_symptom_tag_work(
    entries: Sequence[DailySymptomEntry],
    symptoms: Mapping[uuid.UUID, SymptomRef],
    tags: Mapping[uuid.UUID, TagRef],
    *,
    min_symptom_usages: int,
    min_tag_usages: int,
) -> CooccurrenceWorkPlan:
    symptom_counts = dict.fromkeys(symptoms, 0)
    tag_counts = dict.fromkeys(tags, 0)
    for entry in entries:
        for symptom_id in entry.symptom_ids:
            if symptom_id in symptom_counts:
                symptom_counts[symptom_id] += 1
        for tag_id in entry.tag_ids:
            if tag_id in tag_counts:
                tag_counts[tag_id] += 1
    eligible_symptoms = sum(count >= min_symptom_usages for count in symptom_counts.values())
    eligible_tags = sum(count >= min_tag_usages for count in tag_counts.values())
    pair_count = eligible_symptoms * eligible_tags
    return CooccurrenceWorkPlan(
        supplied_tags=len(tags),
        supplied_symptoms=len(symptoms),
        eligible_tags=eligible_tags,
        eligible_symptoms=eligible_symptoms,
        pair_count=pair_count,
        work_units=len(entries) * pair_count,
    )


def work_limit_reason(plan: CooccurrenceWorkPlan) -> str | None:
    if plan.supplied_tags > settings.COOCCURRENCE_MAX_SUPPLIED_TAGS:
        return "supplied_tags"
    if plan.supplied_symptoms > settings.COOCCURRENCE_MAX_SUPPLIED_SYMPTOMS:
        return "supplied_symptoms"
    if plan.eligible_tags > settings.COOCCURRENCE_MAX_ELIGIBLE_TAGS:
        return "eligible_tags"
    if plan.eligible_symptoms > settings.COOCCURRENCE_MAX_ELIGIBLE_SYMPTOMS:
        return "eligible_symptoms"
    if plan.pair_count > settings.COOCCURRENCE_MAX_PAIRS:
        return "pair_count"
    if plan.work_units > settings.COOCCURRENCE_MAX_WORK_UNITS:
        return "work_units"
    return None


def compute_tag_tag_job(
    entries: Sequence[DailySymptomEntry],
    tags: Mapping[uuid.UUID, TagRef],
    min_tag_usages: int,
    timeout_seconds: float,
) -> list[TagTagAssociation]:
    return heatmap_tag_tag_associations(
        entries,
        tags,
        min_tag_usages=min_tag_usages,
        deadline=time.monotonic() + timeout_seconds,
    )


def compute_symptom_tag_job(
    entries: Sequence[DailySymptomEntry],
    symptoms: Mapping[uuid.UUID, SymptomRef],
    tags: Mapping[uuid.UUID, TagRef],
    min_tag_usages: int,
    timeout_seconds: float,
) -> list[SymptomTagAssociation]:
    return heatmap_symptom_tag_associations(
        entries,
        symptoms,
        tags,
        min_tag_usages=min_tag_usages,
        deadline=time.monotonic() + timeout_seconds,
    )


class CooccurrenceRunner:
    """One bounded process pool per API process.

    Exact duplicate requests share one task. A user may have one distinct job
    admitted at a time, and global queued plus running jobs never exceeds the
    configured worker and queue capacity.
    """

    def __init__(self) -> None:
        self._executor: ProcessPoolExecutor | None = None
        self._lock = asyncio.Lock()
        self._inflight: dict[Hashable, asyncio.Task[Any]] = {}
        self._users: set[uuid.UUID] = set()
        self._cache: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()

    def _get_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=settings.COOCCURRENCE_PROCESS_WORKERS,
                mp_context=multiprocessing.get_context("spawn"),
            )
        return self._executor

    async def run(
        self,
        *,
        key: Hashable,
        user_id: uuid.UUID,
        function: Callable[..., T],
        args: tuple[Any, ...],
    ) -> T:
        now = time.monotonic()
        async with self._lock:
            cached = self._cache.get(key)
            if cached is not None and cached[0] > now:
                self._cache.move_to_end(key)
                return cached[1]
            if cached is not None:
                del self._cache[key]

            task = self._inflight.get(key)
            if task is None:
                capacity = (
                    settings.COOCCURRENCE_PROCESS_WORKERS
                    + settings.COOCCURRENCE_MAX_QUEUE_SIZE
                )
                if user_id in self._users or len(self._inflight) >= capacity:
                    raise CooccurrenceBusyError
                self._users.add(user_id)
                task = asyncio.create_task(
                    self._execute(key=key, user_id=user_id, function=function, args=args)
                )
                self._inflight[key] = task

        # A disconnected duplicate waiter must not cancel the shared job.
        return await asyncio.shield(task)

    async def _execute(
        self,
        *,
        key: Hashable,
        user_id: uuid.UUID,
        function: Callable[..., T],
        args: tuple[Any, ...],
    ) -> T:
        concurrent_future: ConcurrentFuture[T] | None = None
        release_here = True
        try:
            loop = asyncio.get_running_loop()
            concurrent_future = self._get_executor().submit(function, *args)
            future = asyncio.wrap_future(concurrent_future, loop=loop)
            result = await asyncio.wait_for(
                asyncio.shield(future),
                timeout=settings.COOCCURRENCE_JOB_TIMEOUT_SECONDS,
            )
            async with self._lock:
                expires_at = time.monotonic() + settings.COOCCURRENCE_CACHE_TTL_SECONDS
                self._cache[key] = (expires_at, result)
                self._cache.move_to_end(key)
                while len(self._cache) > settings.COOCCURRENCE_CACHE_MAX_ENTRIES:
                    self._cache.popitem(last=False)
            return result
        except (TimeoutError, CooccurrenceComputationTimeout) as exc:
            if concurrent_future is not None and not concurrent_future.done():
                # ProcessPool jobs cannot be stopped once running. Keep the job
                # and user in admission accounting until the worker really exits.
                release_here = False
                concurrent_future.add_done_callback(
                    lambda _future: loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._release(key, user_id))
                    )
                )
            raise CooccurrenceTimeoutError from exc
        except BrokenProcessPool as exc:
            executor = self._executor
            self._executor = None
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)
            raise CooccurrenceWorkerError from exc
        except Exception as exc:
            raise CooccurrenceWorkerError from exc
        finally:
            if release_here:
                await self._release(key, user_id)

    async def _release(self, key: Hashable, user_id: uuid.UUID) -> None:
        async with self._lock:
            self._inflight.pop(key, None)
            self._users.discard(user_id)

    def shutdown(self) -> None:
        executor = self._executor
        self._executor = None
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)


cooccurrence_runner = CooccurrenceRunner()
