"""Regression coverage for the web-container healthcheck (#1003).

The production web image listens on IPv4 loopback in the affected container
environment. BusyBox ``wget`` may resolve ``localhost`` to ``::1`` first and
report the container unhealthy even though the server is reachable on
``127.0.0.1``. Keep every shipped stack on the unambiguous IPv4 target while
retaining a real HTTP probe that fails when the web server stops.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

WEB_COMPOSE_FILES = (
    REPO_ROOT / "infra" / "docker" / "docker-compose.yml",
    REPO_ROOT / "infra" / "docker" / "docker-compose.quickstart.yml",
    REPO_ROOT / "infra" / "docker" / "docker-compose.user-test.yml",
    REPO_ROOT / "infra" / "dockhand" / "compose.yaml",
    REPO_ROOT / "infra" / "dockge" / "compose.yaml",
)

_HEALTHCHECK = "wget -qO- http://127.0.0.1:3000 > /dev/null 2>&1 || exit 1"


@pytest.mark.parametrize("compose_path", WEB_COMPOSE_FILES, ids=lambda path: path.name)
def test_web_healthcheck_uses_ipv4_loopback(compose_path: Path) -> None:
    assert compose_path.is_file(), f"missing compose file: {compose_path}"
    text = compose_path.read_text(encoding="utf-8")
    assert _HEALTHCHECK in text, (
        f"{compose_path.relative_to(REPO_ROOT)} must probe the running web server "
        "through IPv4 loopback so localhost/IPv6 resolution cannot cause a false "
        "unhealthy result"
    )
