"""Validate A12 gate state and prevent unsupported acceptance claims."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REGISTER = Path(__file__).with_name("A12_ACCEPTANCE_REGISTER.json")
EXPECTED_GATES = {
    "research_h4",
    "health_connect_m8",
    "hosted_beta",
    "firebase_play",
    "compare_device",
    "runtime_security",
    "deployment_restore",
}
GATE_STATUSES = {"pending", "blocked_external", "failed", "passed"}
STEP_STATUSES = {"pending", "failed", "passed"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _candidate_is_immutable(candidate: dict[str, Any]) -> bool:
    return bool(
        isinstance(candidate.get("git_sha"), str)
        and SHA_RE.fullmatch(candidate["git_sha"])
        and all(
            isinstance(candidate.get(key), str) and DIGEST_RE.fullmatch(candidate[key])
            for key in ("api_image_digest", "web_image_digest", "worker_image_digest")
        )
        and candidate.get("staging_deployment_id")
        and candidate.get("deployed_at_utc")
    )


def main() -> None:
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert SHA_RE.fullmatch(data["audit_basis"])

    gates = data["gates"]
    assert {gate["id"] for gate in gates} == EXPECTED_GATES
    assert len(gates) == len(EXPECTED_GATES)

    immutable_candidate = _candidate_is_immutable(data["release_candidate"])
    for gate in gates:
        assert gate["status"] in GATE_STATUSES
        assert gate["owner_role"].strip()
        assert gate["tracking_issues"]
        assert gate["required_evidence"]
        assert isinstance(gate["evidence"], list)

        if gate["status"] == "blocked_external":
            assert gate["blocking_reason"].strip()
        if gate["status"] == "failed":
            assert gate["evidence"], f"{gate['id']}: failed requires failure evidence"
        if gate["status"] == "passed":
            assert immutable_candidate, f"{gate['id']}: passed requires immutable candidate"
            assert gate["evidence"], f"{gate['id']}: passed requires evidence"
            signoff = gate["signoff"]
            assert signoff and signoff.get("role") and signoff.get("date")
            assert signoff.get("result") == "passed"

    deployment = next(gate for gate in gates if gate["id"] == "deployment_restore")
    staging = deployment["staging"]
    production = deployment["production_smoke"]
    assert staging["status"] in STEP_STATUSES
    assert production["status"] in STEP_STATUSES
    if staging["status"] == "passed":
        assert immutable_candidate and staging["evidence"]
    if production["status"] == "passed":
        assert staging["status"] == "passed"
        assert production["evidence"]

    passed = sum(gate["status"] == "passed" for gate in gates)
    print(f"A12 register verified: {len(gates)} gates, {passed} passed")


if __name__ == "__main__":
    main()
