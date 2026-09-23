"""Reproducible capacity benchmark for interactive co-occurrence analytics.

This measures representative CPU cost for budget calibration. It is not a
production latency SLO; staging load tests remain the release gate.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import date, timedelta

from app.models.entry import WorkContext
from app.services.cooccurrence_runtime import (
    compute_symptom_tag_job,
    compute_tag_tag_job,
    plan_symptom_tag_work,
    plan_tag_tag_work,
)
from app.services.symptom_analytics import DailySymptomEntry, SymptomRef, TagRef


def _id(kind: str, index: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"correlcore-benchmark:{kind}:{index}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--tags", type=int, default=20)
    parser.add_argument("--symptoms", type=int, default=20)
    args = parser.parse_args()

    tag_ids = [_id("tag", index) for index in range(args.tags)]
    symptom_ids = [_id("symptom", index) for index in range(args.symptoms)]
    tags = {
        signal_id: TagRef(id=signal_id, label=f"Tag {index}", slug=f"tag-{index:02d}")
        for index, signal_id in enumerate(tag_ids)
    }
    symptoms = {
        signal_id: SymptomRef(
            id=signal_id,
            label=f"Symptom {index}",
            slug=f"symptom-{index:02d}",
        )
        for index, signal_id in enumerate(symptom_ids)
    }
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=day),
            mood_score=3,
            energy=3,
            stress=3,
            tag_ids=frozenset(
                signal_id
                for index, signal_id in enumerate(tag_ids)
                if (day + index * 3) % 11 < 5
            ),
            symptom_ids=frozenset(
                signal_id
                for index, signal_id in enumerate(symptom_ids)
                if (day + index * 5) % 13 < 6
            ),
            work_context=WorkContext.OFFICE if day % 3 == 0 else WorkContext.HOMEOFFICE,
        )
        for day in range(args.days)
    ]

    measurements = []
    for name, plan, function, function_args in (
        (
            "tag_tag",
            plan_tag_tag_work(entries, tags, min_tag_usages=5),
            compute_tag_tag_job,
            (entries, tags, 5, 120.0),
        ),
        (
            "symptom_tag",
            plan_symptom_tag_work(
                entries,
                symptoms,
                tags,
                min_symptom_usages=5,
                min_tag_usages=5,
            ),
            compute_symptom_tag_job,
            (entries, symptoms, tags, 5, 120.0),
        ),
    ):
        started = time.perf_counter()
        result = function(*function_args)
        measurements.append(
            {
                "analysis": name,
                "days": args.days,
                "eligible_tags": plan.eligible_tags,
                "eligible_symptoms": plan.eligible_symptoms,
                "pairs": plan.pair_count,
                "work_units": plan.work_units,
                "result_count": len(result),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }
        )

    print(json.dumps(measurements, indent=2))


if __name__ == "__main__":
    main()
