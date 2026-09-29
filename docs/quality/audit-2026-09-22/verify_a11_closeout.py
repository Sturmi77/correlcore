"""Verify that the A11 review closeout remains lossless and fully dispositioned."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


REGISTER = Path(__file__).with_name("A11_REVIEW_CLOSEOUT.csv")
EXPECTED_ROWS = 524
EXPECTED_KINDS = Counter({"Inline": 298, "Review/Antwort": 226})
EXPECTED_CURRENT_PRS = Counter(
    {"968": 3, "969": 6, "970": 5, "971": 8, "972": 11, "973": 23, "974": 8}
)


def main() -> None:
    with REGISTER.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == EXPECTED_ROWS, f"expected {EXPECTED_ROWS} rows, got {len(rows)}"
    assert Counter(row["art"] for row in rows) == EXPECTED_KINDS
    assert len({row["url"] for row in rows}) == EXPECTED_ROWS, "review URLs must be unique"

    historic = [row for row in rows if int(row["pr"]) <= 963]
    current = [row for row in rows if int(row["pr"]) >= 968]
    assert len(historic) == 460
    assert len(current) == 64
    assert Counter(row["pr"] for row in current) == EXPECTED_CURRENT_PRS

    required = ("url", "auditZuordnung", "abschlussgruppe", "abschlussstatus", "abschlussnachweis")
    for number, row in enumerate(rows, start=2):
        missing = [field for field in required if not row[field].strip()]
        assert not missing, f"row {number} has empty fields: {', '.join(missing)}"

    for row in current:
        if row["art"] == "Review/Antwort":
            assert row["abschlussgruppe"].endswith(":review-summary")
        elif row["pr"] in {"972", "973"}:
            assert row["isResolved"] == "true"
            assert row["abschlussstatus"] == "behoben; Regressionstest auf main verankert"

    print(f"A11 closeout verified: {len(rows)} unique, dispositioned review rows")


if __name__ == "__main__":
    main()
