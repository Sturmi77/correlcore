"""M7 tag clustering service based on co-occurrence vectors."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.tag import EntryTag, Tag
from app.schemas.stats import TagClusterGroup, TagClustersResponse, TagCooccurrenceTagRef
from app.services.tag_service import active_tag_predicate

TAG_CLUSTER_WINDOW_DAYS = 90
MIN_TAG_CLUSTER_ENTRIES = 90
MIN_TAG_CLUSTER_ACTIVE_TAGS = 5
MIN_TAG_CLUSTER_K = 3
MAX_TAG_CLUSTER_K = 6


@dataclass(frozen=True)
class DailyTagSet:
    entry_date: date_type
    tag_ids: frozenset[uuid.UUID]


@dataclass(frozen=True)
class TagVectorSet:
    daily_entries: tuple[DailyTagSet, ...]
    tags: tuple[Tag, ...]
    vectors: dict[uuid.UUID, tuple[float, ...]]

    @property
    def entry_count(self) -> int:
        return len(self.daily_entries)

    @property
    def active_tag_count(self) -> int:
        return len(self.tags)


def _today() -> date_type:
    return datetime.now(UTC).date()


def _tag_ref(tag: Tag) -> TagCooccurrenceTagRef:
    return TagCooccurrenceTagRef(
        tag_id=tag.id,
        slug=tag.slug,
        name=tag.name,
        category=tag.category,
        color=tag.color,
    )


def _insufficient(
    *,
    entry_count: int,
    active_tag_count: int,
    reason: str,
    window_days: int,
) -> TagClustersResponse:
    return TagClustersResponse(
        status="insufficient_data",
        entry_count=entry_count,
        active_tag_count=active_tag_count,
        window_days=window_days,
        reason=reason,
        clusters=[],
    )


def build_tag_vectors(
    daily_entries: Sequence[DailyTagSet],
    tags: Sequence[Tag],
) -> TagVectorSet:
    """Build one Jaccard co-occurrence vector per active tag."""

    ordered_tags = tuple(sorted(tags, key=lambda tag: (tag.slug, str(tag.id))))
    ordered_ids = [tag.id for tag in ordered_tags]
    tag_counts = {
        tag_id: sum(1 for entry in daily_entries if tag_id in entry.tag_ids)
        for tag_id in ordered_ids
    }
    pair_counts: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
    for entry in daily_entries:
        present = sorted(entry.tag_ids & set(ordered_ids), key=str)
        for index, left in enumerate(present):
            for right in present[index + 1 :]:
                pair_counts[(left, right)] += 1
                pair_counts[(right, left)] += 1

    vectors: dict[uuid.UUID, tuple[float, ...]] = {}
    for left_id in ordered_ids:
        row: list[float] = []
        for right_id in ordered_ids:
            if left_id == right_id:
                row.append(1.0)
                continue
            co_count = pair_counts.get((left_id, right_id), 0)
            union_count = tag_counts[left_id] + tag_counts[right_id] - co_count
            row.append(round(co_count / union_count, 6) if union_count else 0.0)
        vectors[left_id] = tuple(row)

    return TagVectorSet(
        daily_entries=tuple(daily_entries),
        tags=ordered_tags,
        vectors=vectors,
    )


def _choose_cluster_count(matrix: np.ndarray, *, tag_count: int) -> int | None:
    max_k = min(MAX_TAG_CLUSTER_K, tag_count - 1)
    if max_k < MIN_TAG_CLUSTER_K:
        return None

    unique_rows = np.unique(matrix, axis=0).shape[0]
    max_k = min(max_k, unique_rows)
    if max_k < MIN_TAG_CLUSTER_K:
        return None

    best_k = MIN_TAG_CLUSTER_K
    best_score = float("-inf")
    for k in range(MIN_TAG_CLUSTER_K, max_k + 1):
        labels = KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(matrix)
        if len(set(labels)) < 2:
            continue
        score = float(silhouette_score(matrix, labels))
        if score > best_score:
            best_k = k
            best_score = score
    return best_k


def _cluster_strength(
    cluster_tag_ids: Sequence[uuid.UUID],
    vectors: dict[uuid.UUID, tuple[float, ...]],
    tag_index: dict[uuid.UUID, int],
) -> float:
    if len(cluster_tag_ids) < 2:
        return 0.0
    values: list[float] = []
    for index, left_id in enumerate(cluster_tag_ids):
        for right_id in cluster_tag_ids[index + 1 :]:
            values.append(vectors[left_id][tag_index[right_id]])
    return round(sum(values) / len(values), 4) if values else 0.0


def build_tag_cluster_response(
    vector_set: TagVectorSet,
    *,
    window_days: int = TAG_CLUSTER_WINDOW_DAYS,
) -> TagClustersResponse:
    """Cluster tag vectors with k-means or return an insufficient-data response."""

    if vector_set.entry_count < MIN_TAG_CLUSTER_ENTRIES:
        return _insufficient(
            entry_count=vector_set.entry_count,
            active_tag_count=vector_set.active_tag_count,
            reason="entry_count_below_90",
            window_days=window_days,
        )
    if vector_set.active_tag_count < MIN_TAG_CLUSTER_ACTIVE_TAGS:
        return _insufficient(
            entry_count=vector_set.entry_count,
            active_tag_count=vector_set.active_tag_count,
            reason="active_tag_count_below_5",
            window_days=window_days,
        )

    tag_ids = [tag.id for tag in vector_set.tags]
    matrix = np.array([vector_set.vectors[tag_id] for tag_id in tag_ids], dtype=float)
    k = _choose_cluster_count(matrix, tag_count=len(tag_ids))
    if k is None:
        return _insufficient(
            entry_count=vector_set.entry_count,
            active_tag_count=vector_set.active_tag_count,
            reason="not_enough_vector_variance",
            window_days=window_days,
        )

    labels = KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(matrix)
    tags_by_id = {tag.id: tag for tag in vector_set.tags}
    tag_index = {tag_id: index for index, tag_id in enumerate(tag_ids)}
    grouped: dict[int, list[uuid.UUID]] = defaultdict(list)
    for tag_id, label in zip(tag_ids, labels, strict=True):
        grouped[int(label)].append(tag_id)

    clusters: list[TagClusterGroup] = []
    for ordinal, (_, cluster_tag_ids) in enumerate(
        sorted(
            grouped.items(),
            key=lambda item: (-len(item[1]), min(tags_by_id[tag_id].slug for tag_id in item[1])),
        ),
        start=1,
    ):
        ordered_cluster_ids = sorted(cluster_tag_ids, key=lambda tag_id: tags_by_id[tag_id].slug)
        cluster_tags = [_tag_ref(tags_by_id[tag_id]) for tag_id in ordered_cluster_ids]
        clusters.append(
            TagClusterGroup(
                cluster_id=ordinal,
                label=f"Tag group {ordinal}",
                tags=cluster_tags,
                strength=_cluster_strength(ordered_cluster_ids, vector_set.vectors, tag_index),
            )
        )

    return TagClustersResponse(
        status="ok",
        entry_count=vector_set.entry_count,
        active_tag_count=vector_set.active_tag_count,
        window_days=window_days,
        k=k,
        clusters=clusters,
    )


async def _load_tag_vector_inputs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
    window_days: int,
) -> TagVectorSet:
    start_date = as_of - timedelta(days=window_days - 1)
    entry_result = await db.execute(
        select(Entry)
        .where(
            Entry.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= as_of,
        )
        .order_by(Entry.entry_date.asc(), Entry.slot.asc())
    )
    entries = list(entry_result.scalars().all())

    tag_result = await db.execute(
        select(Entry.entry_date, Tag)
        .join(EntryTag, EntryTag.entry_id == Entry.id)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .where(
            Entry.user_id == user_id,
            EntryTag.user_id == user_id,
            Entry.entry_date >= start_date,
            Entry.entry_date <= as_of,
            active_tag_predicate(user_id),
        )
        .order_by(Entry.entry_date.asc(), Tag.slug.asc())
    )

    tag_ids_by_date: dict[date_type, set[uuid.UUID]] = defaultdict(set)
    tags_by_id: dict[uuid.UUID, Tag] = {}
    for entry_date, tag in tag_result.all():
        tag_ids_by_date[entry_date].add(tag.id)
        tags_by_id[tag.id] = tag

    daily_entries = [
        DailyTagSet(
            entry_date=entry_date,
            tag_ids=frozenset(tag_ids_by_date.get(entry_date, set())),
        )
        for entry_date in sorted({entry.entry_date for entry in entries})
    ]
    return build_tag_vectors(daily_entries, list(tags_by_id.values()))


async def _upsert_tag_vectors(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    vector_set: TagVectorSet,
    as_of: date_type,
    window_days: int,
) -> None:
    if not vector_set.vectors:
        return

    window_start = as_of - timedelta(days=window_days - 1)
    tag_order = [str(tag.id) for tag in vector_set.tags]
    stmt = text(
        """
        INSERT INTO tag_vectors (
            user_id,
            tag_id,
            embedding,
            tag_order,
            window_start,
            window_end,
            entry_count,
            active_tag_count,
            computed_at
        )
        VALUES (
            :user_id,
            :tag_id,
            CAST(:embedding AS vector),
            CAST(:tag_order AS jsonb),
            :window_start,
            :window_end,
            :entry_count,
            :active_tag_count,
            now()
        )
        ON CONFLICT (user_id, tag_id) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            tag_order = EXCLUDED.tag_order,
            window_start = EXCLUDED.window_start,
            window_end = EXCLUDED.window_end,
            entry_count = EXCLUDED.entry_count,
            active_tag_count = EXCLUDED.active_tag_count,
            computed_at = EXCLUDED.computed_at
        """
    )
    for tag_id, vector in vector_set.vectors.items():
        await db.execute(
            stmt,
            {
                "user_id": user_id,
                "tag_id": tag_id,
                "embedding": "[" + ",".join(f"{value:.6f}" for value in vector) + "]",
                "tag_order": json.dumps(tag_order),
                "window_start": window_start,
                "window_end": as_of,
                "entry_count": vector_set.entry_count,
                "active_tag_count": vector_set.active_tag_count,
            },
        )


async def recompute_tag_vectors_and_clusters(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
    window_days: int = TAG_CLUSTER_WINDOW_DAYS,
    persist_vectors: bool = True,
) -> TagClustersResponse:
    """Recompute tag vectors and return the current clustering response."""

    as_of = as_of or _today()
    vector_set = await _load_tag_vector_inputs(
        db, user_id=user_id, as_of=as_of, window_days=window_days
    )
    if persist_vectors:
        await _upsert_tag_vectors(
            db,
            user_id=user_id,
            vector_set=vector_set,
            as_of=as_of,
            window_days=window_days,
        )
    return build_tag_cluster_response(vector_set, window_days=window_days)


async def get_tag_clusters(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
) -> TagClustersResponse:
    """Return current tag groups, recomputing vectors on demand for freshness."""

    return await recompute_tag_vectors_and_clusters(db, user_id=user_id, as_of=as_of)
