"""Release evidence must reflect running image identity and scanner coverage."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).parents[2]


def load_script(relative):
    spec = importlib.util.spec_from_file_location("a10_test_script", ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "running,image_id,revision_ok",
    [(False, "sha256:good", True), (True, "sha256:other", True), (True, "sha256:good", False)],
)
def test_runtime_identity_rejects_wrong_or_stopped_image(
    monkeypatch, running, image_id, revision_ok
):
    module = load_script("scripts/a10-runtime-images.py")
    revision = "a" * 40
    monkeypatch.setattr(
        module.sys,
        "argv",
        [
            "check",
            revision,
            "api",
            "ghcr.io/test/api@sha256:" + "b" * 64,
            "web",
            "ghcr.io/test/web@sha256:" + "c" * 64,
        ],
    )
    monkeypatch.setattr(
        module,
        "inspect",
        lambda kind, name: (
            {"State": {"Running": running}, "Image": image_id}
            if kind == "container"
            else {
                "Id": "sha256:good",
                "Config": {
                    "Labels": {
                        "org.opencontainers.image.revision": revision if revision_ok else "wrong"
                    }
                },
            }
        ),
    )
    with pytest.raises(RuntimeError):
        module.main()


def test_scan_coverage_records_rate_limits_without_sensitive_messages(monkeypatch):
    module = load_script(".zap/a10-coverage-hook.py")
    output = Mock()
    monkeypatch.setattr(module, "Path", lambda path: SimpleNamespace(write_text=output))
    messages = [
        {"responseHeader": "HTTP/1.1 429 Too Many Requests", "requestHeader": "secret"},
        {"responseHeader": "HTTP/1.1 200 OK"},
    ]
    module.zap_pre_shutdown(
        SimpleNamespace(core=SimpleNamespace(messages=lambda **kwargs: messages))
    )
    assert json.loads(output.call_args.args[0]) == {"429": 1, "200": 1}
    assert "secret" not in output.call_args.args[0]
