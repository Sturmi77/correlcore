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
MOBILE_GATES = {"health_connect_m8", "firebase_play", "compare_device"}
GATE_STATUSES = {"pending", "blocked_external", "failed", "passed", "not_applicable"}
STEP_STATUSES = {"pending", "failed", "passed"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _require(condition: object, message: str) -> None:
    """Raise a persistent validation error even when assertions are disabled."""

    if not condition:
        raise ValueError(message)


def _candidate_is_immutable(
    candidate: object, *, require_android: bool = False
) -> bool:
    if not isinstance(candidate, dict):
        return False
    immutable = bool(
        isinstance(candidate.get("git_sha"), str)
        and SHA_RE.fullmatch(candidate["git_sha"])
        and all(
            isinstance(candidate.get(key), str) and DIGEST_RE.fullmatch(candidate[key])
            for key in ("api_image_digest", "web_image_digest", "worker_image_digest")
        )
        and candidate.get("staging_deployment_id")
        and candidate.get("deployed_at_utc")
    )
    if require_android:
        immutable = immutable and bool(
            isinstance(candidate.get("android_artifact_digest"), str)
            and DIGEST_RE.fullmatch(candidate["android_artifact_digest"])
        )
    return immutable


def _candidate_identity(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(
        candidate.get(key)
        for key in (
            "git_sha",
            "api_image_digest",
            "web_image_digest",
            "worker_image_digest",
            "android_artifact_digest",
        )
    )


def _require_signoff(scope: dict[str, Any], label: str, result: str) -> None:
    signoff = scope.get("signoff")
    _require(isinstance(signoff, dict), f"{label}: {result} requires sign-off")
    _require(signoff.get("role"), f"{label}: sign-off role is required")
    _require(signoff.get("date"), f"{label}: sign-off date is required")
    _require(
        signoff.get("result") == result, f"{label}: sign-off result must be {result}"
    )


def _require_bound_candidate(
    scope: dict[str, Any],
    release_candidate: dict[str, Any],
    label: str,
    *,
    require_android: bool = False,
) -> None:
    candidate = scope.get("candidate")
    _require(
        isinstance(candidate, dict),
        f"{label}: passed evidence requires candidate snapshot",
    )
    _require(
        _candidate_is_immutable(candidate, require_android=require_android),
        f"{label}: candidate snapshot must be immutable",
    )
    _require(
        _candidate_identity(candidate) == _candidate_identity(release_candidate),
        f"{label}: evidence/sign-off candidate differs from release candidate",
    )


def main() -> None:
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    _require(data.get("schema_version") == 1, "schema_version must be 1")
    _require(
        isinstance(data.get("audit_basis"), str)
        and SHA_RE.fullmatch(data["audit_basis"]),
        "audit_basis must be a full git SHA",
    )

    gates = data.get("gates")
    _require(isinstance(gates, list), "gates must be a list")
    _require(
        {gate.get("id") for gate in gates} == EXPECTED_GATES,
        "gate ids do not match A12",
    )
    _require(len(gates) == len(EXPECTED_GATES), "A12 gates must be unique")

    release_candidate = data.get("release_candidate")
    _require(isinstance(release_candidate, dict), "release_candidate must be an object")
    immutable_candidate = _candidate_is_immutable(release_candidate)
    for gate in gates:
        gate_id = gate["id"]
        status = gate.get("status")
        _require(status in GATE_STATUSES, f"{gate_id}: invalid status")
        _require(
            str(gate.get("owner_role", "")).strip(),
            f"{gate_id}: owner role is required",
        )
        _require(
            gate.get("tracking_issues"), f"{gate_id}: tracking issues are required"
        )
        _require(
            gate.get("required_evidence"), f"{gate_id}: required evidence is required"
        )
        _require(
            isinstance(gate.get("evidence"), list),
            f"{gate_id}: evidence must be a list",
        )

        if status == "blocked_external":
            _require(
                str(gate.get("blocking_reason", "")).strip(),
                f"{gate_id}: blocked_external requires a reason",
            )
        if status == "failed":
            _require(gate["evidence"], f"{gate_id}: failed requires failure evidence")
        if status == "not_applicable":
            _require(
                str(gate.get("not_applicable_reason", "")).strip(),
                f"{gate_id}: not_applicable requires a scope rationale",
            )
            _require_signoff(gate, gate_id, "not_applicable")
        if status == "passed":
            require_android = gate_id in MOBILE_GATES
            _require(
                immutable_candidate, f"{gate_id}: passed requires immutable candidate"
            )
            _require_bound_candidate(
                gate,
                release_candidate,
                gate_id,
                require_android=require_android,
            )
            _require(gate["evidence"], f"{gate_id}: passed requires evidence")
            _require_signoff(gate, gate_id, "passed")

    deployment = next(gate for gate in gates if gate["id"] == "deployment_restore")
    staging = deployment["staging"]
    production = deployment["production_smoke"]
    _require(
        staging.get("status") in STEP_STATUSES, "deployment staging has invalid status"
    )
    _require(
        production.get("status") in STEP_STATUSES, "production smoke has invalid status"
    )
    if staging["status"] == "passed":
        _require(
            immutable_candidate and staging.get("evidence"),
            "passed staging needs evidence",
        )
        _require_bound_candidate(
            staging, release_candidate, "deployment_restore.staging"
        )
    if production["status"] == "passed":
        _require(
            staging["status"] == "passed", "production smoke requires passed staging"
        )
        _require(production.get("evidence"), "passed production smoke needs evidence")
        _require_bound_candidate(
            production, release_candidate, "deployment_restore.production_smoke"
        )
    if deployment["status"] == "passed":
        _require(
            staging["status"] == "passed", "deployment gate requires passed staging"
        )
        _require(
            production["status"] == "passed",
            "deployment gate requires passed production smoke",
        )

    passed = sum(gate["status"] == "passed" for gate in gates)
    not_applicable = sum(gate["status"] == "not_applicable" for gate in gates)
    print(
        f"A12 register verified: {len(gates)} gates, {passed} passed, "
        f"{not_applicable} not applicable"
    )


if __name__ == "__main__":
    main()
