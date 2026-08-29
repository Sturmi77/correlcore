#!/usr/bin/env python
"""Export the FastAPI OpenAPI schema to a deterministic JSON file.

Single source of truth for the frontend type generation in
``packages/api-types`` (issue #778, audit Q2). Import the app, call
``app.openapi()`` and write the schema with sorted keys so the committed
snapshot only changes when the actual contract changes — CI regenerates and
diffs it to catch silent FE/BE drift.

Usage::

    uv run --python 3.12 python scripts/export_openapi.py [OUTPUT]

``OUTPUT`` defaults to ``<repo>/packages/api-types/openapi.json``. Only the
schema is produced — no database, Redis or network access is required — so the
script seeds harmless placeholder secrets when they are absent, letting it run
in any checkout without a configured environment.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Settings validate on import (key lengths, Fernet validity). The schema does
# not depend on their values, so provide valid-shaped placeholders when unset.
_ENV_DEFAULTS = {
    "APP_ENV": "test",
    "SECRET_KEY": "openapi-export-secret-key-min-32-bytes-pad",
    "ENCRYPTION_KEY": "SFt_zAqsk202KSZePwlHDy3TkhiHG1rFDBePciArND4=",
    "SLUG_HMAC_KEY": "openapi-export-slug-hmac-key-32-bytes-pad",
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
    "REDIS_URL": "redis://:changeme@localhost:6379/0",
}
for key, value in _ENV_DEFAULTS.items():
    os.environ.setdefault(key, value)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT = _REPO_ROOT / "packages" / "api-types" / "openapi.json"


def _serialize(schema: dict[str, object]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    output = Path(argv[1]) if len(argv) > 1 else _DEFAULT_OUTPUT

    # Imported after env defaults are seeded so settings validation passes.
    from app.main import app

    schema = app.openapi()
    rendered = _serialize(schema)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {len(rendered)} bytes to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
