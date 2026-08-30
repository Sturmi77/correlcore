#!/usr/bin/env python3
"""Generate the secondary homelab Compose stacks from one canonical source (#781).

Audit **M10 / D-I1**: CorrelCore ships several near-duplicate homelab Compose
files (user-test, dockge, dockhand) that drift from the canonical quickstart —
an env var added to one is silently missed in the others (e.g. the
COOKIE_SECURE-across-four-stacks class of bug in ADR-0006).

Single source of truth
----------------------
``infra/docker/docker-compose.quickstart.yml`` is the hand-maintained canonical
homelab stack (shared service shape + the ``x-api-env`` environment block). The
secondary stacks are **derived** from it here: each is the canonical stack with a
small, explicit overlay (project name, container-name prefix, Docker network
name, host port bindings, whether GlitchTip ships, and a header comment). The
shared environment therefore lives in exactly one place; a change to it
propagates to every stack on regeneration.

Usage
-----
PyYAML is the only dependency; run under uv so a fresh checkout needs no manual
install (there is no root Python project — PyYAML otherwise only lives in the
backend uv environment)::

    uv run --no-project --with "pyyaml>=6,<7" python scripts/gen_compose_stacks.py
    uv run --no-project --with "pyyaml>=6,<7" python scripts/gen_compose_stacks.py --check

Regeneration is enforced in CI (``.github/workflows/ci-compose.yml``). The
generated files carry a DO-NOT-EDIT banner; edit this script (or the canonical
quickstart) and regenerate instead.

Safety
------
Only ``${VAR}`` interpolation references appear in the output — never resolved
secret material. ``--check`` and the CI job additionally validate every stack
with ``docker compose config`` when Docker is available.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "infra" / "docker" / "docker-compose.quickstart.yml"

# The canonical stack's own identity, stripped/rewritten for each derived stack.
_SRC_PROJECT = "correlcore-quickstart"
_SRC_PREFIX = "correlcore-quickstart-"
_SRC_NETWORK = "internal"

# Host-published API port binding used by the stacks that expose the API on the
# host instead of only within the Compose network.
_API_PUBLISH = ["${TAILSCALE_IP:-127.0.0.1}:${API_HOST_PORT:-8210}:8000"]


def _web_ports(web_default: str) -> list[str]:
    return [f"${{TAILSCALE_IP:-127.0.0.1}}:${{WEB_HOST_PORT:-{web_default}}}:3000"]


# Per-stack overlays — the *only* intentional differences from the canonical
# quickstart stack. Everything else (service shape, healthchecks, the shared
# x-api-env) is inherited, so it cannot drift.
# Docker resource identity (volume + network `name:`) that must be PRESERVED so
# an existing deployment reattaches its live data instead of Compose allocating
# new project-prefixed volumes. ``None`` means "unnamed" (Compose prefixes with
# the project name, matching the stack's current behavior).
STACKS: dict[str, dict[str, Any]] = {
    "infra/docker/docker-compose.user-test.yml": {
        "project": "correlcore-test",
        "prefix": "correlcore-test-",
        "network": "internal",
        "network_name": None,
        "volume_names": None,
        "web_default": "3000",
        "publish_api": True,
        "logging": False,
        "glitchtip": True,
        "header": [
            "CorrelCore — Compose stack for published-image user tests (GHCR).",
            "Tailscale-internal homelab (no Traefik/TLS); ports bind to the",
            "Tailscale/loopback interface only. Profiles: `worker`, `monitoring`.",
            "",
            "Start:  cp .env.example .env  &&  edit  &&",
            "        docker compose -f docker-compose.user-test.yml up -d",
        ],
    },
    "infra/dockge/compose.yaml": {
        # No top-level name on purpose: Dockge deploys from a per-stack folder
        # (documented /opt/stacks/correlcore), and Compose then uses that folder
        # as the project name. Forcing a name here would change the project
        # identity and collide with the existing fixed-name correlcore-*
        # containers on an in-place upgrade.
        "project": None,
        "prefix": "correlcore-",
        "network": "correlcore",
        "network_name": "correlcore",
        "volume_names": {
            "postgres_data": "correlcore_postgres_data",
            "redis_data": "correlcore_redis_data",
        },
        "web_default": "3000",
        "publish_api": True,
        "logging": False,
        "glitchtip": False,
        "header": [
            "CorrelCore — Dockge drop-in stack.",
            "Copy compose.yaml + .env to /opt/stacks/correlcore/ and Deploy in the",
            "Dockge UI. Tailscale-internal homelab (no Traefik/TLS); ports bind to",
            "${TAILSCALE_IP} (default 127.0.0.1). GlitchTip is omitted here; use the",
            "user-test or quickstart stack (profile `monitoring`) for error tracking.",
        ],
    },
    "infra/dockhand/compose.yaml": {
        "project": "correlcore",
        "prefix": "correlcore-",
        "network": "correlcore",
        "network_name": "correlcore",
        "volume_names": {
            "postgres_data": "correlcore_postgres_data",
            "redis_data": "correlcore_redis_data",
        },
        "web_default": "3010",
        "publish_api": False,
        # Dockhand pins per-service json-file log rotation (owner preference).
        "logging": {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}},
        "glitchtip": True,
        "header": [
            "CorrelCore — Dockhand drop-in stack (https://dockhand.pro).",
            "Git-stack: New → From Git, path infra/dockhand, branch main.",
            "Tailscale-internal homelab (no Traefik/TLS). Per ADR-0011 the API is",
            "not published on the host: the web container proxies /api/* to",
            "http://api:8000 inside the Compose network. Profiles: `worker`,",
            "`monitoring`.",
        ],
    },
}

_BANNER = [
    "============================================================================",
    "GENERATED FILE — DO NOT EDIT.",
    "Generated from infra/docker/docker-compose.quickstart.yml by",
    "scripts/gen_compose_stacks.py (#781). Edit the canonical quickstart stack or",
    "that script and run `python scripts/gen_compose_stacks.py`, then commit.",
    "See docs/selfhost/COMPOSE_STACKS.md.",
    "============================================================================",
]


def _load_canonical() -> dict[str, Any]:
    with CANONICAL.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _rename_network(compose: dict[str, Any], new_network: str) -> None:
    if new_network == _SRC_NETWORK:
        return
    networks = compose.get("networks", {})
    if _SRC_NETWORK in networks:
        networks[new_network] = networks.pop(_SRC_NETWORK)
    for svc in compose.get("services", {}).values():
        svc_nets = svc.get("networks")
        if isinstance(svc_nets, list):
            svc["networks"] = [new_network if n == _SRC_NETWORK else n for n in svc_nets]


def _reprefix_containers(compose: dict[str, Any], new_prefix: str) -> None:
    if new_prefix == _SRC_PREFIX:
        return
    for svc in compose.get("services", {}).values():
        name = svc.get("container_name")
        if isinstance(name, str) and name.startswith(_SRC_PREFIX):
            svc["container_name"] = new_prefix + name[len(_SRC_PREFIX) :]


def _set_resource_names(overlay: dict[str, Any], compose: dict[str, Any]) -> None:
    """Preserve explicit Docker volume/network ``name:`` identity (data safety).

    Without an explicit ``name`` Compose prefixes the resource with the project
    name, so a stack that previously pinned ``correlcore_postgres_data`` would
    start an empty ``<project>_postgres_data`` and appear to lose its data.
    """
    net_name = overlay.get("network_name")
    if net_name:
        compose["networks"][overlay["network"]]["name"] = net_name
    vol_names = overlay.get("volume_names")
    if vol_names:
        for vol, name in vol_names.items():
            compose["volumes"][vol] = {"name": name}


def _apply_env_overrides(overlay: dict[str, Any], compose: dict[str, Any]) -> None:
    """Per-stack env corrections applied to every service that carries the key.

    - ``FRONTEND_BASE_URL``'s default host port must track the stack's actual web
      port default, or links/emails point at the wrong port when WEB_HOST_PORT is
      unset.
    - ``RATE_LIMIT_TRUST_PROXY_HEADERS`` must be ``false`` where the API is
      published directly on the host: with no trusted proxy in front, a client
      could otherwise spoof ``X-Forwarded-For`` to dodge rate limits
      (docs/DEVELOPMENT.md). Stacks that keep the API Compose-internal inherit the
      canonical ``true`` (the web container is the trusted hop).
    """
    web_default = overlay["web_default"]
    for svc in compose.get("services", {}).values():
        env = svc.get("environment")
        if not isinstance(env, dict):
            continue
        if isinstance(env.get("FRONTEND_BASE_URL"), str):
            env["FRONTEND_BASE_URL"] = env["FRONTEND_BASE_URL"].replace(
                "WEB_HOST_PORT:-3010", f"WEB_HOST_PORT:-{web_default}"
            )
        if overlay["publish_api"] and "RATE_LIMIT_TRUST_PROXY_HEADERS" in env:
            env["RATE_LIMIT_TRUST_PROXY_HEADERS"] = "false"


def _apply_logging(overlay: dict[str, Any], compose: dict[str, Any]) -> None:
    logging = overlay.get("logging")
    if not logging:
        return
    for svc in compose.get("services", {}).values():
        svc["logging"] = copy.deepcopy(logging)


def _build_stack(overlay: dict[str, Any]) -> dict[str, Any]:
    compose = copy.deepcopy(_load_canonical())

    # The image/anchor helper keys are inlined into each service by the YAML
    # merge on load, so the top-level `x-*-image` aliases are dead weight in the
    # generated output. (`x-api-env` stays: it is still referenced as an anchor.)
    compose.pop("x-api-image", None)
    compose.pop("x-web-image", None)

    # A stack with an explicit project name pins it; one with project=None omits
    # the key so Compose derives the project from the deploy directory (Dockge).
    if overlay["project"] is None:
        compose.pop("name", None)
    else:
        compose["name"] = overlay["project"]
    _reprefix_containers(compose, overlay["prefix"])
    _rename_network(compose, overlay["network"])

    services = compose["services"]

    # Web host port default (interface + container port are unchanged).
    services["web"]["ports"] = _web_ports(overlay["web_default"])

    # API: publish on the host, or keep it Compose-network-internal (expose).
    api = services["api"]
    if overlay["publish_api"]:
        api.pop("expose", None)
        api["ports"] = list(_API_PUBLISH)
    # else: inherit the canonical `expose: ['8000']` (no host binding).

    if not overlay["glitchtip"]:
        services.pop("glitchtip", None)

    _set_resource_names(overlay, compose)
    _apply_env_overrides(overlay, compose)
    _apply_logging(overlay, compose)

    return compose


def _render(overlay: dict[str, Any]) -> str:
    compose = _build_stack(overlay)
    header = "\n".join(f"# {line}".rstrip() for line in [*_BANNER, "", *overlay["header"]])
    # width high enough that long ${VAR} values (e.g. DATABASE_URL) are never
    # folded mid-value, which keeps the generated YAML readable and greppable.
    body = yaml.safe_dump(compose, sort_keys=False, default_flow_style=False, width=4096)
    return f"{header}\n\n{body}"


def _contains_secret_literal(text: str) -> list[str]:
    """Guard: generated output must carry only ${VAR} refs, never resolved secrets."""
    offenders: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#") or ":" not in line:
            continue
        _, _, value = line.partition(":")
        value = value.strip().strip("'\"")
        lowered = line.lower()
        looks_secret = any(k in lowered for k in ("password", "secret_key", "secret:", "hmac"))
        if looks_secret and value and "${" not in value and value not in {"", "|", ">"}:
            offenders.append(raw.strip())
    return offenders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any generated stack is out of date (no writes).",
    )
    args = parser.parse_args()

    stale: list[str] = []
    for rel_path, overlay in STACKS.items():
        rendered = _render(overlay)

        offenders = _contains_secret_literal(rendered)
        if offenders:
            print(f"::error::{rel_path} would contain non-interpolated secret material:")
            for off in offenders:
                print(f"  {off}")
            return 2

        target = REPO_ROOT / rel_path
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if args.check:
            if current != rendered:
                stale.append(rel_path)
        else:
            target.write_text(rendered, encoding="utf-8")
            print(f"wrote {rel_path}")

    if args.check and stale:
        print("::error::Generated Compose stacks are out of date:")
        for path in stale:
            print(f"  {path}")
        print("Run `python scripts/gen_compose_stacks.py` and commit the result.")
        return 1

    if args.check:
        print("All generated Compose stacks are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
