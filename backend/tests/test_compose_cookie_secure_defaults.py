"""Regression: HTTP Homelab compose stacks must default COOKIE_SECURE=false.

Without this, ``APP_ENV=staging`` + unset ``COOKIE_SECURE`` emits Secure
cookies. Browsers on ``http://`` Tailscale origins discard them (RFC 6265bis)
and every authenticated call returns 401 ``Could not validate credentials``.

Dockhand and quickstart already had the default; user-test and dockge did not
— this test locks all four HTTP-oriented stacks.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

HTTP_HOMELAB_COMPOSE_FILES = (
    REPO_ROOT / "infra" / "docker" / "docker-compose.user-test.yml",
    REPO_ROOT / "infra" / "docker" / "docker-compose.quickstart.yml",
    REPO_ROOT / "infra" / "dockhand" / "compose.yaml",
    REPO_ROOT / "infra" / "dockge" / "compose.yaml",
)

_COOKIE_SECURE_FALSE_DEFAULT = re.compile(
    r"COOKIE_SECURE:\s*\$\{COOKIE_SECURE:-false\}",
)


@pytest.mark.parametrize("compose_path", HTTP_HOMELAB_COMPOSE_FILES, ids=lambda p: p.name)
def test_http_homelab_compose_defaults_cookie_secure_false(compose_path: Path) -> None:
    assert compose_path.is_file(), f"missing compose file: {compose_path}"
    text = compose_path.read_text(encoding="utf-8")
    assert _COOKIE_SECURE_FALSE_DEFAULT.search(text), (
        f"{compose_path.relative_to(REPO_ROOT)} must set "
        "COOKIE_SECURE: ${COOKIE_SECURE:-false} for plain-HTTP Homelab "
        "(otherwise staging Secure cookies → silent login then API 401)"
    )
