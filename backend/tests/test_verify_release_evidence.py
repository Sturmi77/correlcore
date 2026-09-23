from __future__ import annotations

from copy import deepcopy

from scripts.verify_release_evidence import REQUIRED_GATES, validate

SHA = "a" * 40
API_IMAGE = f"ghcr.io/example/api@sha256:{'b' * 64}"
WEB_IMAGE = f"ghcr.io/example/web@sha256:{'c' * 64}"


def _manifest() -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "release": {"sha": SHA, "apiImage": API_IMAGE, "webImage": WEB_IMAGE},
        "evidence": [
            {
                "gate": gate,
                "status": "passed",
                "sha": SHA,
                "apiImage": API_IMAGE,
                "webImage": WEB_IMAGE,
                "url": f"https://github.com/example/repo/actions/runs/1#{gate}",
                "completedAt": "2026-09-23T12:00:00Z",
            }
            for gate in sorted(REQUIRED_GATES)
        ],
    }


def test_complete_manifest_passes() -> None:
    assert validate(_manifest()) == []


def test_pending_or_cross_release_evidence_fails() -> None:
    manifest = deepcopy(_manifest())
    evidence = manifest["evidence"]
    assert isinstance(evidence, list)
    evidence[0]["status"] = "pending"
    evidence[1]["sha"] = "d" * 40
    evidence[2]["webImage"] = f"ghcr.io/example/web@sha256:{'e' * 64}"

    errors = validate(manifest)

    assert any("status must be passed" in error for error in errors)
    assert any("sha does not match" in error for error in errors)
    assert any("image digests do not match" in error for error in errors)


def test_mutable_image_and_missing_gate_fail() -> None:
    manifest = _manifest()
    release = manifest["release"]
    evidence = manifest["evidence"]
    assert isinstance(release, dict)
    assert isinstance(evidence, list)
    release["apiImage"] = "ghcr.io/example/api:latest"
    evidence.pop()

    errors = validate(manifest)

    assert any("pinned by sha256" in error for error in errors)
    assert any("missing gates" in error for error in errors)


def test_duplicate_gate_and_unknown_schema_fail() -> None:
    manifest = _manifest()
    evidence = manifest["evidence"]
    assert isinstance(evidence, list)
    evidence[-1] = deepcopy(evidence[0])
    manifest["schemaVersion"] = 2

    errors = validate(manifest)

    assert any("schemaVersion must be 1" in error for error in errors)
    assert any("exactly once" in error for error in errors)
