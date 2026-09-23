"""Validate that every A10 release gate refers to one immutable candidate."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
REQUIRED_GATES = {
    "linux-ci",
    "windows-timezone",
    "migration",
    "real-api-e2e",
    "security-dependency",
    "performance",
    "visual-a11y",
}


def validate(payload: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["manifest must be a JSON object"]
    if payload.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")

    release = payload.get("release")
    if not isinstance(release, dict):
        return ["release must be an object"]

    sha = release.get("sha")
    api_image = release.get("apiImage")
    web_image = release.get("webImage")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        errors.append("release.sha must be a lowercase 40-character commit SHA")
    for name, value in (("apiImage", api_image), ("webImage", web_image)):
        if not isinstance(value, str) or not IMAGE_RE.fullmatch(value):
            errors.append(f"release.{name} must be pinned by sha256 digest")

    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        return [*errors, "evidence must be an array"]

    names = {item.get("gate") for item in evidence if isinstance(item, dict)}
    if len(evidence) != len(REQUIRED_GATES) or len(names) != len(evidence):
        errors.append("evidence must contain every required gate exactly once")
    missing = REQUIRED_GATES - names
    extra = names - REQUIRED_GATES
    if missing:
        errors.append(f"missing gates: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unknown gates: {', '.join(sorted(str(name) for name in extra))}")

    for index, item in enumerate(evidence):
        prefix = f"evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if item.get("status") != "passed":
            errors.append(f"{prefix}.status must be passed")
        if item.get("sha") != sha:
            errors.append(f"{prefix}.sha does not match release.sha")
        if item.get("apiImage") != api_image or item.get("webImage") != web_image:
            errors.append(f"{prefix} image digests do not match the release")
        url = item.get("url")
        parsed = urlparse(url) if isinstance(url, str) else None
        if parsed is None or parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{prefix}.url must be an absolute HTTPS evidence link")
        if not isinstance(item.get("completedAt"), str) or not item["completedAt"].endswith("Z"):
            errors.append(f"{prefix}.completedAt must be a UTC timestamp")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_release_evidence.py <manifest.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{path}: {exc}", file=sys.stderr)
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"{path}: {error}", file=sys.stderr)
        return 1
    print(f"{path}: complete A10 evidence for {payload['release']['sha']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
