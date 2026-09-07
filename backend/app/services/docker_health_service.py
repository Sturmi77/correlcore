"""Optional Docker container status for developer diagnostics.

ADR-0015 forbids mounting the Docker socket into the API container. This
module only talks to the Engine API over ``DOCKER_HOST`` / ``DEV_DOCKER_HOST``
(typically ``tcp://socket-proxy:2375``) or the host ``docker`` CLI when that
binary is on PATH (local uvicorn). Failures are swallowed — the /dev view
still has application-level probes.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from app.core.config import settings
from app.schemas.dev import DevContainerHealth

logger = logging.getLogger(__name__)

_EXIT_CODE_RE = re.compile(r"Exited \((\-?\d+)\)", re.IGNORECASE)
_STACK_NAME_RE = re.compile(r"^correlcore", re.IGNORECASE)
_COMPOSE_PROJECT_PREFIX = "correlcore"
_CLI_TIMEOUT_SECONDS = 3.0
_HTTP_TIMEOUT_SECONDS = 2.0


def list_stack_containers() -> list[DevContainerHealth]:
    raw_rows = _load_raw_containers()
    containers = [_normalize_container(row) for row in raw_rows]
    return [container for container in containers if _is_stack_container(container)]


def _load_raw_containers() -> list[dict[str, Any]]:
    http_base = _engine_http_base()
    if http_base:
        rows = _list_via_engine_http(http_base)
        if rows is not None:
            return rows
    return _list_via_cli()


def _engine_http_base() -> str | None:
    configured = (settings.DEV_DOCKER_HOST or os.environ.get("DOCKER_HOST") or "").strip()
    if configured.startswith("tcp://") or configured.startswith("http://"):
        return configured
    return None


def _list_via_engine_http(docker_host: str) -> list[dict[str, Any]] | None:
    parsed = urlparse(docker_host if "://" in docker_host else f"tcp://{docker_host}")
    host = parsed.hostname
    if not host:
        return None
    port = parsed.port or 2375
    url = f"http://{host}:{port}/containers/json?all=true"
    try:
        with urlopen(url, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.info("dev docker engine list skipped: %s", type(exc).__name__)
        return None
    if not isinstance(payload, list):
        return None
    return [row for row in payload if isinstance(row, dict)]


def _list_via_cli() -> list[dict[str, Any]]:
    docker = shutil.which("docker")
    if not docker:
        return []
    try:
        completed = subprocess.run(
            [docker, "ps", "-a", "--format", "{{json .}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_CLI_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.info("dev docker cli list skipped: %s", type(exc).__name__)
        return []
    if completed.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _normalize_container(raw: dict[str, Any]) -> DevContainerHealth:
    name = _container_name(raw)
    labels = _labels(raw)
    service = labels.get("com.docker.compose.service") or _service_from_name(name) or name
    state = str(raw.get("State") or "unknown").lower()
    status = str(raw.get("Status") or "")
    health = _health_from_status(status)
    exit_code = _exit_code_from_status(status)
    issue = _issue_for(state=state, health=health, service=service, name=name, exit_code=exit_code)
    return DevContainerHealth(
        name=name,
        service=service,
        state=state,
        health=health,
        exit_code=exit_code,
        issue=issue,
        status_text=status,
    )


def _container_name(raw: dict[str, Any]) -> str:
    names = raw.get("Names")
    if isinstance(names, list) and names:
        return str(names[0]).lstrip("/")
    if isinstance(names, str) and names:
        return names.split(",")[0].lstrip("/")
    return str(raw.get("Name") or raw.get("ID") or raw.get("Id") or "unknown").lstrip("/")


def _labels(raw: dict[str, Any]) -> dict[str, str]:
    labels = raw.get("Labels")
    if isinstance(labels, dict):
        return {str(key): str(value) for key, value in labels.items()}
    if isinstance(labels, str) and labels:
        parsed: dict[str, str] = {}
        for part in labels.split(","):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            parsed[key.strip()] = value.strip()
        return parsed
    return {}


def _service_from_name(name: str) -> str:
    stripped = re.sub(r"^correlcore(?:-[a-z0-9]+)?-", "", name, flags=re.IGNORECASE)
    return stripped or name


def _health_from_status(status: str) -> str:
    lower = status.lower()
    if "(unhealthy)" in lower:
        return "unhealthy"
    if "(health: starting)" in lower:
        return "starting"
    if "(healthy)" in lower:
        return "healthy"
    return "none"


def _exit_code_from_status(status: str) -> int | None:
    match = _EXIT_CODE_RE.search(status)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _is_stack_container(container: DevContainerHealth) -> bool:
    if _STACK_NAME_RE.match(container.name):
        return True
    return container.service not in {"", container.name} and container.name.startswith(
        _COMPOSE_PROJECT_PREFIX
    )


def _is_clean_one_shot(service: str, name: str, state: str, exit_code: int | None) -> bool:
    haystack = f"{service} {name}".lower()
    if "migrate" not in haystack:
        return False
    return state == "exited" and exit_code == 0


def _issue_for(
    *,
    state: str,
    health: str,
    service: str,
    name: str,
    exit_code: int | None,
) -> str:
    if _is_clean_one_shot(service, name, state, exit_code):
        return "none"
    if health == "unhealthy":
        return "unhealthy"
    if state in {"exited", "dead", "paused", "stopped", "restarting"}:
        return "stopped"
    return "none"
