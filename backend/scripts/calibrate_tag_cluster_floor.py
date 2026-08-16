#!/usr/bin/env python3
"""Calibrate the tag-cluster ``STRENGTH_FLOOR`` with a permutation null model.

Context (#706)
==============
Tag groups are ranked and (proposed) filtered by ``_cluster_strength`` — the
**mean pairwise Jaccard co-occurrence** within a group, in ``[0, 1]``. K-Means
always emits *k* clusters, even from near-random data, so a floor is needed to
drop "chance" groups and avoid presenting noise as a real pattern. Hard-coding a
constant (e.g. ``0.2``) is indefensible; this harness derives the floor from
data so the choice is reproducible and honest.

Method — degree-preserving permutation null
===========================================
For each maturity bucket (entry counts spanning early / provisional / robust) we
generate many synthetic users in two arms and run the **real** clustering
pipeline (``build_tag_vectors`` → ``build_tag_cluster_response``) on both:

* **POSITIVE control** — tags are organised into latent groups that genuinely
  co-occur, at a per-rep signal strength drawn across the strong→borderline
  range (plus independent per-tag baseline noise). Groups here *should* survive
  the floor.
* **NULL control** — the *same* per-tag daily incidence, but each tag's day
  assignments are independently permuted (column shuffle). This preserves every
  tag's marginal frequency while destroying co-occurrence, so any group the
  clusterer still finds is **pure chance**. Its strengths define the "chance
  ceiling".

The floor candidate is a high percentile (P95 / P99) of the NULL strengths: a
group is shown only when its cohesion exceeds what independent tags produce by
chance ~95–99 % of the time. We then report how many POSITIVE groups survive
that floor (sensitivity) and whether a single constant works across buckets or a
per-bucket (sample-size-aware) floor is warranted — chance co-occurrence is
higher with fewer entries, so this matters.

Determinism
===========
K-Means uses ``random_state=0`` inside the service, so clustering is
deterministic per vector set; all randomness here comes from the synthetic data
generation and is seeded (``--seed``) for reproducibility.

Usage
=====
    uv run --python 3.12 python scripts/calibrate_tag_cluster_floor.py
    # more reps + machine-readable output:
    uv run python scripts/calibrate_tag_cluster_floor.py --reps 400 --json out.json

This script has **no side effects** (no DB, no network) and does not modify the
application. It only prints (and optionally writes) the calibration report. The
resulting floor + a regression test are applied separately as part of #706.
"""

from __future__ import annotations

import argparse
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from app.models.tag import Tag, TagCategory
from app.services.tag_cluster_service import (
    DailyTagSet,
    build_tag_cluster_response,
    build_tag_vectors,
)

# Representative entry counts per maturity tier (thresholds: 30 / 45 / 90).
DEFAULT_BUCKETS: dict[str, int] = {"early": 35, "provisional": 60, "robust": 120}
_CATEGORIES = list(TagCategory)


@dataclass
class ClusterObservation:
    bucket: str
    arm: str  # "positive" | "null"
    strength: float
    size: int


def _make_tag(index: int) -> Tag:
    """Build a detached ``Tag`` with just the fields the vector pipeline reads."""
    t = Tag()
    t.id = uuid.uuid4()
    t.user_id = uuid.uuid4()
    t.slug = f"tag-{index:02d}"
    t.name = f"Tag {index:02d}"
    t.category = _CATEGORIES[index % len(_CATEGORIES)]
    t.icon = None
    t.color = None
    t.is_default = False
    t.is_hidden = False
    t.include_in_analytics = True
    t.habit_type = "none"
    t.target_frequency = None
    return t


def _positive_incidence(
    rng: np.random.Generator,
    *,
    n_days: int,
    groups: list[list[int]],
    n_tags: int,
    signal: float,
    noise: float,
) -> np.ndarray:
    """Days × tags boolean matrix with latent co-occurring groups.

    On each day one group is "active" (its members light up with prob ``signal``)
    and every tag additionally fires independently with prob ``noise``.
    """
    incidence = rng.random((n_days, n_tags)) < noise
    active_group = rng.integers(0, len(groups), size=n_days)
    for day in range(n_days):
        for member in groups[active_group[day]]:
            if rng.random() < signal:
                incidence[day, member] = True
    return incidence


def _null_incidence(rng: np.random.Generator, incidence: np.ndarray) -> np.ndarray:
    """Independently permute each tag's day assignments (degree-preserving null)."""
    out = incidence.copy()
    n_days = out.shape[0]
    for col in range(out.shape[1]):
        out[:, col] = out[rng.permutation(n_days), col]
    return out


def _incidence_to_daily(incidence: np.ndarray, tags: list[Tag]) -> list[DailyTagSet]:
    start = date(2026, 1, 1)
    daily: list[DailyTagSet] = []
    for day in range(incidence.shape[0]):
        tag_ids = frozenset(tags[j].id for j in range(len(tags)) if incidence[day, j])
        daily.append(DailyTagSet(entry_date=start + timedelta(days=day), tag_ids=tag_ids))
    return daily


def _cluster_index_set(cluster: object, id_to_index: dict[uuid.UUID, int]) -> frozenset[int]:
    members = getattr(cluster, "members", None)
    ids = (
        [m.signal_id for m in members] if members else [t.tag_id for t in cluster.tags]  # type: ignore[attr-defined]
    )
    return frozenset(id_to_index[i] for i in ids if i in id_to_index)


def _matches_planted(index_set: frozenset[int], groups: list[list[int]]) -> bool:
    """A cluster is a genuine group if it Jaccard-overlaps a planted group >= 0.5."""
    best = 0.0
    for group in groups:
        gs = set(group)
        union = len(index_set | gs)
        if union:
            best = max(best, len(index_set & gs) / union)
    return best >= 0.5


def _collect_clusters(
    daily: list[DailyTagSet], tags: list[Tag]
) -> list[tuple[float, int, frozenset[int]]]:
    """Run the real clustering pipeline; return (strength, size, member_index_set)."""
    response = build_tag_cluster_response(build_tag_vectors(daily, tags))
    if response.status != "ok":
        return []
    id_to_index = {tag.id: index for index, tag in enumerate(tags)}
    return [
        (
            cluster.strength,
            len(cluster.members or cluster.tags),
            _cluster_index_set(cluster, id_to_index),
        )
        for cluster in response.clusters
    ]


def _make_groups(rng: np.random.Generator, n_tags: int) -> list[list[int]]:
    """Partition tag indices into 3 latent groups of size 2–3 (rest are noise-only)."""
    order = list(rng.permutation(n_tags))
    groups: list[list[int]] = []
    cursor = 0
    for size in (3, 2, 2):
        if cursor + size > n_tags:
            break
        groups.append(order[cursor : cursor + size])
        cursor += size
    return groups


def run_bucket(
    rng: np.random.Generator, *, bucket: str, n_days: int, reps: int, n_tags: int
) -> tuple[list[ClusterObservation], int]:
    observations: list[ClusterObservation] = []
    insufficient = 0
    for _ in range(reps):
        tags = [_make_tag(i) for i in range(n_tags)]
        groups = _make_groups(rng, n_tags)
        signal = float(rng.uniform(0.5, 0.95))  # strong → borderline
        noise = 0.05
        pos = _positive_incidence(
            rng, n_days=n_days, groups=groups, n_tags=n_tags, signal=signal, noise=noise
        )
        null = _null_incidence(rng, pos)

        pos_clusters = _collect_clusters(_incidence_to_daily(pos, tags), tags)
        null_clusters = _collect_clusters(_incidence_to_daily(null, tags), tags)
        if not pos_clusters and not null_clusters:
            insufficient += 1
        for strength, size, index_set in pos_clusters:
            # Separate the *genuine* (planted) groups from the incidental noise
            # clusters K-Means also emits, so sensitivity measures real groups only.
            arm = "positive_planted" if _matches_planted(index_set, groups) else "positive_noise"
            observations.append(ClusterObservation(bucket, arm, strength, size))
        for strength, size, _index_set in null_clusters:
            observations.append(ClusterObservation(bucket, "null", strength, size))
    return observations, insufficient


def _pct(values: list[float], q: float) -> float:
    return float(np.percentile(values, q)) if values else float("nan")


def summarize(observations: list[ClusterObservation], buckets: dict[str, int]) -> dict:
    report: dict = {"buckets": {}, "recommendation": {}}
    null_p95_by_bucket: dict[str, float] = {}
    for bucket in buckets:
        null = [o.strength for o in observations if o.bucket == bucket and o.arm == "null"]
        pos = [
            o.strength for o in observations if o.bucket == bucket and o.arm == "positive_planted"
        ]
        noise = [
            o.strength for o in observations if o.bucket == bucket and o.arm == "positive_noise"
        ]
        null_p95 = _pct(null, 95)
        null_p99 = _pct(null, 99)
        null_p95_by_bucket[bucket] = null_p95
        # sensitivity/specificity at the P95-null floor
        pos_survive = (
            float(np.mean([s >= null_p95 for s in pos]))
            if pos and not np.isnan(null_p95)
            else float("nan")
        )
        null_filtered = (
            float(np.mean([s < null_p95 for s in null]))
            if null and not np.isnan(null_p95)
            else float("nan")
        )
        report["buckets"][bucket] = {
            "n_null_clusters": len(null),
            "n_pos_clusters": len(pos),  # genuine (planted-matching) groups only
            "n_noise_clusters": len(noise),
            "noise_p50": _pct(noise, 50),
            "null_p90": _pct(null, 90),
            "null_p95": null_p95,
            "null_p99": null_p99,
            "pos_p5": _pct(pos, 5),
            "pos_p25": _pct(pos, 25),
            "pos_p50": _pct(pos, 50),
            "sensitivity_at_p95": pos_survive,  # fraction of real groups kept
            "specificity_at_p95": null_filtered,  # fraction of null groups dropped
        }
    finite = [v for v in null_p95_by_bucket.values() if not np.isnan(v)]
    constant_floor = max(finite) if finite else float("nan")  # conservative single value
    spread = (max(finite) - min(finite)) if finite else float("nan")
    report["recommendation"] = {
        "null_p95_by_bucket": null_p95_by_bucket,
        "constant_floor_p95": constant_floor,
        "p95_spread_across_buckets": spread,
        "note": (
            "Use the constant floor if the spread is small; otherwise adopt the "
            "per-bucket P95 (sample-size-aware). P99 is the stricter alternative."
        ),
    }
    return report


def _print_report(report: dict) -> None:
    print("\n=== Tag-cluster strength floor calibration (permutation null) ===\n")
    header = (
        f"{'bucket':<12}{'n_pos':>7}{'n_null':>7}"
        f"{'null_p95':>10}{'null_p99':>10}{'pos_p5':>9}{'pos_p50':>9}"
        f"{'sens@p95':>10}{'spec@p95':>10}"
    )
    print(header)
    print("-" * len(header))
    for bucket, b in report["buckets"].items():
        print(
            f"{bucket:<12}{b['n_pos_clusters']:>7}{b['n_null_clusters']:>7}"
            f"{b['null_p95']:>10.3f}{b['null_p99']:>10.3f}{b['pos_p5']:>9.3f}{b['pos_p50']:>9.3f}"
            f"{b['sensitivity_at_p95']:>10.2f}{b['specificity_at_p95']:>10.2f}"
        )
    rec = report["recommendation"]
    print("\nRecommendation:")
    print(
        f"  null-P95 by bucket : { {k: round(v, 3) for k, v in rec['null_p95_by_bucket'].items()} }"
    )
    print(f"  constant floor (max null-P95) : {rec['constant_floor_p95']:.3f}")
    print(f"  P95 spread across buckets     : {rec['p95_spread_across_buckets']:.3f}")
    print(f"  {rec['note']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reps", type=int, default=300, help="synthetic users per bucket per arm")
    parser.add_argument("--tags", type=int, default=10, help="active tags per synthetic user")
    parser.add_argument("--seed", type=int, default=1234, help="RNG seed (reproducibility)")
    parser.add_argument("--json", type=str, default=None, help="write the full report to this path")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    all_obs: list[ClusterObservation] = []
    insufficient_by_bucket: dict[str, int] = defaultdict(int)
    for bucket, n_days in DEFAULT_BUCKETS.items():
        obs, insufficient = run_bucket(
            rng, bucket=bucket, n_days=n_days, reps=args.reps, n_tags=args.tags
        )
        all_obs.extend(obs)
        insufficient_by_bucket[bucket] = insufficient

    report = summarize(all_obs, DEFAULT_BUCKETS)
    report["config"] = {
        "reps": args.reps,
        "tags": args.tags,
        "seed": args.seed,
        "buckets": DEFAULT_BUCKETS,
        "insufficient_reps_by_bucket": dict(insufficient_by_bucket),
    }
    _print_report(report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Wrote full report to {args.json}")


if __name__ == "__main__":
    main()
