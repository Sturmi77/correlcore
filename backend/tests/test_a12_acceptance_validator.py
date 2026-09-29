"""Regression coverage for the executable A12 acceptance guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "docs/quality/audit-2026-09-22/verify_a12_acceptance.py"
REGISTER = VALIDATOR.with_name("A12_ACCEPTANCE_REGISTER.json")


def _run_validator(
    tmp_path: Path, data: dict[str, Any], *, optimized: bool = False
) -> subprocess.CompletedProcess[str]:
    script = tmp_path / VALIDATOR.name
    script.write_text(VALIDATOR.read_text(encoding="utf-8"), encoding="utf-8")
    script.with_name(REGISTER.name).write_text(json.dumps(data), encoding="utf-8")
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.append(str(script))
    return subprocess.run(command, check=False, capture_output=True, text=True)


def test_validator_cannot_be_disabled_with_python_optimize(tmp_path: Path) -> None:
    invalid = json.loads(REGISTER.read_text(encoding="utf-8"))
    invalid["schema_version"] = 999

    result = _run_validator(tmp_path, invalid, optimized=True)

    assert result.returncode != 0
    assert "schema_version must be 1" in result.stderr


def test_mobile_gate_requires_android_artifact_digest(tmp_path: Path) -> None:
    candidate = {
        "git_sha": "a" * 40,
        "api_image_digest": f"sha256:{'b' * 64}",
        "web_image_digest": f"sha256:{'c' * 64}",
        "worker_image_digest": f"sha256:{'d' * 64}",
        "android_artifact_digest": None,
        "staging_deployment_id": "deploy-1",
        "deployed_at_utc": "2026-09-23T12:00:00Z",
    }
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    data["release_candidate"] = candidate
    gate = next(gate for gate in data["gates"] if gate["id"] == "health_connect_m8")
    gate.update(
        status="passed",
        candidate=candidate.copy(),
        evidence=["device matrix"],
        signoff={"role": "Mobile QA", "date": "2026-09-23", "result": "passed"},
    )

    result = _run_validator(tmp_path, data)

    assert result.returncode != 0
    assert "candidate snapshot must be immutable" in result.stderr


def test_not_applicable_gate_accepts_scope_signoff(tmp_path: Path) -> None:
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    gate = next(gate for gate in data["gates"] if gate["id"] == "firebase_play")
    gate.update(
        status="not_applicable",
        not_applicable_reason="This release does not ship an Android application.",
        signoff={
            "role": "Release",
            "date": "2026-09-23",
            "result": "not_applicable",
        },
    )

    result = _run_validator(tmp_path, data)

    assert result.returncode == 0, result.stderr
    assert "1 not applicable" in result.stdout
