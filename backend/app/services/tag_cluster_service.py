"""M7 tag clustering service based on co-occurrence vectors."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from typing import Literal

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag
from app.models.user_preference import UserPreference
from app.schemas.stats import (
    TagClusterGroup,
    TagClusterMember,
    TagClustersResponse,
    TagCooccurrenceTagRef,
)
from app.services.tag_service import active_tag_predicate

TAG_CLUSTER_WINDOW_DAYS = 90
MIN_TAG_CLUSTER_ENTRIES = 90
MIN_TAG_CLUSTER_ACTIVE_TAGS = 5
MIN_SIGNAL_CLUSTER_NODES = 5
MIN_TAG_CLUSTER_K = 3
MAX_TAG_CLUSTER_K = 6


@dataclass(frozen=True)
class DailyTagSet:
    entry_date: date_type
    tag_ids: frozenset[uuid.UUID]
    symptom_ids: frozenset[uuid.UUID] = frozenset()


@dataclass(frozen=True)
class SignalNode:
    kind: str
    node_id: uuid.UUID
    slug: str
    name: str
    icon: str | None = None
    category: str | None = None
    color: str | None = None


@dataclass(frozen=True)
class TagVectorSet:
    daily_entries: tuple[DailyTagSet, ...]
    tags: tuple[Tag, ...]
    vectors: dict[uuid.UUID, tuple[float, ...]]
    nodes: tuple[SignalNode, ...] = ()

    @property
    def entry_count(self) -> int:
        return len(self.daily_entries)

    @property
    def active_tag_count(self) -> int:
        return len(self.tags)

    @property
    def active_signal_count(self) -> int:
        return len(self.nodes) if self.nodes else len(self.tags)


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


def _canonicalize_tags_by_slug(
    tags_by_slug: dict[str, list[Tag]],
) -> tuple[dict[uuid.UUID, uuid.UUID], dict[uuid.UUID, Tag]]:
    canonical_tags_by_slug = {
        slug: sorted(tags, key=lambda item: (item.is_default, item.name.casefold(), str(item.id)))[
            0
        ]
        for slug, tags in tags_by_slug.items()
    }
    tag_aliases = {
        tag.id: canonical_tags_by_slug[tag.slug].id
        for tags in tags_by_slug.values()
        for tag in tags
    }
    tags_by_id = {tag.id: tag for tag in canonical_tags_by_slug.values()}
    return tag_aliases, tags_by_id


def _canonicalize_symptoms_by_slug(
    symptoms_by_slug: dict[str, list[Symptom]],
) -> tuple[dict[uuid.UUID, uuid.UUID], dict[uuid.UUID, Symptom]]:
    canonical_symptoms_by_slug = {
        slug: sorted(
            symptoms,
            key=lambda item: (item.is_default, item.display_name.casefold(), str(item.id)),
        )[0]
        for slug, symptoms in symptoms_by_slug.items()
    }
    symptom_aliases = {
        symptom.id: canonical_symptoms_by_slug[symptom.slug].id
        for symptoms in symptoms_by_slug.values()
        for symptom in symptoms
    }
    symptoms_by_id = {symptom.id: symptom for symptom in canonical_symptoms_by_slug.values()}
    return symptom_aliases, symptoms_by_id


def _insufficient(
    *,
    entry_count: int,
    active_tag_count: int,
    active_signal_count: int,
    reason: str,
    window_days: int,
) -> TagClustersResponse:
    return TagClustersResponse(
        status="insufficient_data",
        entry_count=entry_count,
        active_tag_count=active_tag_count,
        active_signal_count=active_signal_count,
        window_days=window_days,
        reason=reason,
        clusters=[],
    )


def _member_from_node(node: SignalNode) -> TagClusterMember:
    return TagClusterMember(
        kind="tag" if node.kind == "tag" else "symptom",
        signal_id=node.node_id,
        slug=node.slug,
        name=node.name,
        icon=node.icon,
        category=node.category,
        color=node.color,
    )


def build_tag_vectors(
    daily_entries: Sequence[DailyTagSet],
    tags: Sequence[Tag],
    symptoms: Sequence[Symptom] = (),
) -> TagVectorSet:
    """Build one Jaccard co-occurrence vector per active tag and symptom."""

    tag_nodes = tuple(
        SignalNode(
            kind="tag",
            node_id=tag.id,
            slug=tag.slug,
            name=tag.name,
            category=tag.category.value if hasattr(tag.category, "value") else str(tag.category),
            color=tag.color,
        )
        for tag in sorted(tags, key=lambda item: (item.slug, str(item.id)))
    )
    symptom_nodes = tuple(
        SignalNode(
            kind="symptom",
            node_id=symptom.id,
            slug=symptom.slug,
            name=symptom.display_name,
            icon=symptom.icon,
        )
        for symptom in sorted(symptoms, key=lambda item: (item.slug, str(item.id)))
    )
    nodes = tag_nodes + symptom_nodes
    ordered_ids = [node.node_id for node in nodes]
    signal_counts = {
        node_id: sum(
            1 for entry in daily_entries if node_id in entry.tag_ids or node_id in entry.symptom_ids
        )
        for node_id in ordered_ids
    }
    pair_counts: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
    for entry in daily_entries:
        present = sorted(
            {
                node_id
                for node_id in ordered_ids
                if node_id in entry.tag_ids or node_id in entry.symptom_ids
            },
            key=str,
        )
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
            union_count = signal_counts[left_id] + signal_counts[right_id] - co_count
            row.append(round(co_count / union_count, 6) if union_count else 0.0)
        vectors[left_id] = tuple(row)

    return TagVectorSet(
        daily_entries=tuple(daily_entries),
        tags=tuple(sorted(tags, key=lambda tag: (tag.slug, str(tag.id)))),
        vectors=vectors,
        nodes=nodes,
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
    """Cluster signal vectors with k-means or return an insufficient-data response."""

    active_signal_count = vector_set.active_signal_count
    if vector_set.entry_count < MIN_TAG_CLUSTER_ENTRIES:
        return _insufficient(
            entry_count=vector_set.entry_count,
            active_tag_count=vector_set.active_tag_count,
            active_signal_count=active_signal_count,
            reason="entry_count_below_90",
            window_days=window_days,
        )
    if active_signal_count < MIN_SIGNAL_CLUSTER_NODES:
        return _insufficient(
            entry_count=vector_set.entry_count,
            active_tag_count=vector_set.active_tag_count,
            active_signal_count=active_signal_count,
            reason="active_signal_count_below_5",
            window_days=window_days,
        )

    nodes = vector_set.nodes or tuple(
        SignalNode(
            kind="tag",
            node_id=tag.id,
            slug=tag.slug,
            name=tag.name,
            category=tag.category.value if hasattr(tag.category, "value") else str(tag.category),
            color=tag.color,
        )
        for tag in vector_set.tags
    )
    node_ids = [node.node_id for node in nodes]
    matrix = np.array([vector_set.vectors[node_id] for node_id in node_ids], dtype=float)
    k = _choose_cluster_count(matrix, tag_count=len(node_ids))
    if k is None:
        return _insufficient(
            entry_count=vector_set.entry_count,
            active_tag_count=vector_set.active_tag_count,
            active_signal_count=active_signal_count,
            reason="not_enough_vector_variance",
            window_days=window_days,
        )

    labels = KMeans(n_clusters=k, random_state=0, n_init=10).fit_predict(matrix)
    nodes_by_id = {node.node_id: node for node in nodes}
    tags_by_id = {tag.id: tag for tag in vector_set.tags}
    node_index = {node_id: index for index, node_id in enumerate(node_ids)}
    grouped: dict[int, list[uuid.UUID]] = defaultdict(list)
    for node_id, label in zip(node_ids, labels, strict=True):
        grouped[int(label)].append(node_id)

    has_symptoms = any(node.kind == "symptom" for node in nodes)
    cluster_kind: Literal["tags_only", "mixed"] = "mixed" if has_symptoms else "tags_only"
    clusters: list[TagClusterGroup] = []
    for ordinal, (_, cluster_node_ids) in enumerate(
        sorted(
            grouped.items(),
            key=lambda item: (
                -len(item[1]),
                min(nodes_by_id[node_id].slug for node_id in item[1]),
            ),
        ),
        start=1,
    ):
        ordered_cluster_ids = sorted(
            cluster_node_ids, key=lambda node_id: nodes_by_id[node_id].slug
        )
        members = [_member_from_node(nodes_by_id[node_id]) for node_id in ordered_cluster_ids]
        cluster_tags = [
            _tag_ref(tags_by_id[node_id])
            for node_id in ordered_cluster_ids
            if node_id in tags_by_id
        ]
        label_prefix = "Signal group" if cluster_kind == "mixed" else "Tag group"
        clusters.append(
            TagClusterGroup(
                cluster_id=ordinal,
                label=f"{label_prefix} {ordinal}",
                tags=cluster_tags,
                members=members,
                cluster_kind=cluster_kind,
                strength=_cluster_strength(ordered_cluster_ids, vector_set.vectors, node_index),
            )
        )

    return TagClustersResponse(
        status="ok",
        entry_count=vector_set.entry_count,
        active_tag_count=vector_set.active_tag_count,
        active_signal_count=active_signal_count,
        window_days=window_days,
        k=k,
        cluster_kind=cluster_kind,
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

    symptom_result = await db.execute(
        select(Entry.entry_date, Symptom)
        .join(EntrySymptom, EntrySymptom.entry_id == Entry.id)
        .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
        .where(
            Entry.user_id == user_id,
            EntrySymptom.user_id == user_id,
            EntrySymptom.intensity > 0,
            Entry.entry_date >= start_date,
            Entry.entry_date <= as_of,
        )
        .order_by(Entry.entry_date.asc(), Symptom.slug.asc())
    )

    raw_tag_ids_by_date: dict[date_type, set[uuid.UUID]] = defaultdict(set)
    raw_symptom_ids_by_date: dict[date_type, set[uuid.UUID]] = defaultdict(set)
    tags_by_slug: dict[str, list[Tag]] = defaultdict(list)
    symptoms_by_slug: dict[str, list[Symptom]] = defaultdict(list)
    for entry_date, tag in tag_result.all():
        raw_tag_ids_by_date[entry_date].add(tag.id)
        tags_by_slug[tag.slug].append(tag)
    for entry_date, symptom in symptom_result.all():
        raw_symptom_ids_by_date[entry_date].add(symptom.id)
        symptoms_by_slug[symptom.slug].append(symptom)

    tag_aliases, tags_by_id = _canonicalize_tags_by_slug(tags_by_slug)
    symptom_aliases, symptoms_by_id = _canonicalize_symptoms_by_slug(symptoms_by_slug)
    tag_ids_by_date = {
        entry_date: {tag_aliases.get(tag_id, tag_id) for tag_id in tag_ids}
        for entry_date, tag_ids in raw_tag_ids_by_date.items()
    }
    symptom_ids_by_date = {
        entry_date: {symptom_aliases.get(symptom_id, symptom_id) for symptom_id in symptom_ids}
        for entry_date, symptom_ids in raw_symptom_ids_by_date.items()
    }

    daily_entries = [
        DailyTagSet(
            entry_date=entry_date,
            tag_ids=frozenset(tag_ids_by_date.get(entry_date, set())),
            symptom_ids=frozenset(symptom_ids_by_date.get(entry_date, set())),
        )
        for entry_date in sorted({entry.entry_date for entry in entries})
    ]
    return build_tag_vectors(
        daily_entries,
        list(tags_by_id.values()),
        list(symptoms_by_id.values()),
    )


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
        if tag_id not in {tag.id for tag in vector_set.tags}:
            continue
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

    preference_result = await db.execute(
        select(UserPreference.analytics_enabled).where(UserPreference.user_id == user_id)
    )
    if preference_result.scalar_one_or_none() is False:
        return _insufficient(
            entry_count=0,
            active_tag_count=0,
            active_signal_count=0,
            reason="analytics_disabled",
            window_days=TAG_CLUSTER_WINDOW_DAYS,
        )

    return await recompute_tag_vectors_and_clusters(db, user_id=user_id, as_of=as_of)
