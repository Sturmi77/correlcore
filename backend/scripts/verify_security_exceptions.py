"""Reject unowned, expired, or unregistered dependency-audit exceptions."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: verify_security_exceptions.py <register.json> <expected-id>...", file=sys.stderr
        )
        return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    entries = payload.get("exceptions", [])
    by_id = {entry.get("id"): entry for entry in entries if isinstance(entry, dict)}
    errors: list[str] = []
    expected = set(sys.argv[2:])
    if set(by_id) != expected:
        errors.append(
            f"registered ids {sorted(by_id)} do not match audit ignores {sorted(expected)}"
        )
    today = date.today()
    for exception_id, entry in by_id.items():
        for field in ("owner", "scope", "reason"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                errors.append(f"{exception_id}: {field} is required")
        try:
            expiry = date.fromisoformat(entry["expiresOn"])
            if expiry < today:
                errors.append(f"{exception_id}: exception expired on {expiry}")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{exception_id}: expiresOn must be an ISO date")
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
