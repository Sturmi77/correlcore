"""Development-only database dump and restore helpers."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)

SAFE_BACKUP_NAME = re.compile(r"^correlcore-dev-\d{8}T\d{6}Z\.dump$")
_PRODUCTION_HOST_MARKERS = ("prod", "production", "staging")


class DevDbOpsError(RuntimeError):
    """Raised when a development dump/restore cannot proceed safely."""


def _backup_dir() -> Path:
    raw = getattr(settings, "DEV_DB_BACKUP_DIR", None) or os.environ.get(
        "DEV_DB_BACKUP_DIR",
        "/tmp/correlcore-backups",
    )
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def require_dev_db_ops_allowed() -> None:
    """Refuse dump/restore outside local development."""

    env = settings.APP_ENV.lower()
    if env not in {"development", "test"}:
        raise DevDbOpsError(
            f"Database dump/restore is only allowed when APP_ENV=development (got {settings.APP_ENV})"
        )


def _parse_database_url(url: str) -> dict[str, str]:
    # Strip SQLAlchemy driver suffix: postgresql+asyncpg://...
    normalized = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    normalized = normalized.replace("postgres+asyncpg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise DevDbOpsError("DATABASE_URL must be a PostgreSQL URL")
    host = parsed.hostname or "localhost"
    if any(marker in host.lower() for marker in _PRODUCTION_HOST_MARKERS):
        raise DevDbOpsError(f"Refusing dump/restore against host {host!r}")
    db = (parsed.path or "/").lstrip("/") or "correlcore"
    return {
        "host": host,
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or "correlcore"),
        "password": unquote(parsed.password or ""),
        "dbname": db,
    }


def _meta_path(dump_path: Path) -> Path:
    return dump_path.with_suffix(dump_path.suffix + ".meta.json")


def _write_meta(dump_path: Path, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = {
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "app_env": settings.APP_ENV,
        "database_url_host": _parse_database_url(settings.DATABASE_URL)["host"],
        "note": "Keep ENCRYPTION_KEY with this dump; ciphertext notes require the same Fernet master key.",
        "ops_ready": False,
    }
    if extra:
        meta.update(extra)
    _meta_path(dump_path).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def _read_meta(dump_path: Path) -> dict[str, Any] | None:
    path = _meta_path(dump_path)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def list_backups() -> tuple[list[dict[str, Any]], str]:
    """Return backup metadata sorted newest-first plus the backup directory."""

    require_dev_db_ops_allowed()
    directory = _backup_dir()
    items: list[dict[str, Any]] = []
    for path in directory.glob("correlcore-dev-*.dump"):
        if not path.is_file() or not SAFE_BACKUP_NAME.match(path.name):
            continue
        stat = path.stat()
        items.append(
            {
                "name": path.name,
                "size_bytes": int(stat.st_size),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                "meta": _read_meta(path),
            }
        )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items, str(directory)


def create_backup(*, alembic_head: str | None = None) -> dict[str, Any]:
    """Create a custom-format pg_dump in DEV_DB_BACKUP_DIR."""

    require_dev_db_ops_allowed()
    directory = _backup_dir()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dump_name = f"correlcore-dev-{stamp}.dump"
    dump_path = directory / dump_name

    conn = _parse_database_url(settings.DATABASE_URL)
    env = os.environ.copy()
    if conn["password"]:
        env["PGPASSWORD"] = conn["password"]

    container = os.environ.get("POSTGRES_CONTAINER", "correlcore-postgres")
    docker = shutil.which("docker")
    try:
        if docker and _docker_container_running(docker, container):
            cmd = [
                docker,
                "exec",
                "-e",
                f"PGPASSWORD={conn['password']}",
                container,
                "pg_dump",
                "-U",
                conn["user"],
                "-Fc",
                "--no-owner",
                conn["dbname"],
            ]
            with dump_path.open("wb") as out:
                completed = subprocess.run(
                    cmd,
                    check=False,
                    stdout=out,
                    stderr=subprocess.PIPE,
                    env=env,
                )
            if completed.returncode != 0:
                raise DevDbOpsError(
                    completed.stderr.decode("utf-8", errors="replace") or "pg_dump via docker failed"
                )
        else:
            pg_dump = shutil.which("pg_dump")
            if not pg_dump:
                raise DevDbOpsError(
                    "Neither docker postgres container nor pg_dump is available for backups"
                )
            cmd = [
                pg_dump,
                "-h",
                conn["host"],
                "-p",
                conn["port"],
                "-U",
                conn["user"],
                "-Fc",
                "--no-owner",
                "-f",
                str(dump_path),
                conn["dbname"],
            ]
            completed = subprocess.run(cmd, check=False, capture_output=True, env=env)
            if completed.returncode != 0:
                raise DevDbOpsError(
                    completed.stderr.decode("utf-8", errors="replace") or "pg_dump failed"
                )
    except Exception:
        if dump_path.exists():
            dump_path.unlink(missing_ok=True)
        raise

    meta = _write_meta(dump_path, extra={"alembic_head": alembic_head})
    stat = dump_path.stat()
    return {
        "name": dump_name,
        "size_bytes": int(stat.st_size),
        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        "meta": meta,
    }


def restore_backup(name: str, *, confirm: bool) -> dict[str, Any]:
    """Restore a named dump into the configured development database."""

    require_dev_db_ops_allowed()
    if not confirm:
        raise DevDbOpsError("Restore requires confirm=true")
    if not SAFE_BACKUP_NAME.match(name):
        raise DevDbOpsError("Invalid backup name")

    dump_path = _backup_dir() / name
    if not dump_path.is_file():
        raise DevDbOpsError(f"Backup not found: {name}")

    conn = _parse_database_url(settings.DATABASE_URL)
    env = os.environ.copy()
    if conn["password"]:
        env["PGPASSWORD"] = conn["password"]

    container = os.environ.get("POSTGRES_CONTAINER", "correlcore-postgres")
    docker = shutil.which("docker")
    if docker and _docker_container_running(docker, container):
        cmd = [
            docker,
            "exec",
            "-i",
            "-e",
            f"PGPASSWORD={conn['password']}",
            container,
            "pg_restore",
            "-U",
            conn["user"],
            "-d",
            conn["dbname"],
            "--clean",
            "--if-exists",
            "--no-owner",
            "--role",
            conn["user"],
            "-",
        ]
        with dump_path.open("rb") as dump_file:
            completed = subprocess.run(
                cmd,
                check=False,
                stdin=dump_file,
                capture_output=True,
                env=env,
            )
    else:
        pg_restore = shutil.which("pg_restore")
        if not pg_restore:
            raise DevDbOpsError(
                "Neither docker postgres container nor pg_restore is available for restore"
            )
        cmd = [
            pg_restore,
            "-h",
            conn["host"],
            "-p",
            conn["port"],
            "-U",
            conn["user"],
            "-d",
            conn["dbname"],
            "--clean",
            "--if-exists",
            "--no-owner",
            "--role",
            conn["user"],
            str(dump_path),
        ]
        completed = subprocess.run(cmd, check=False, capture_output=True, env=env)

    # pg_restore often exits 1 with benign "errors ignored on restore"; treat
    # hard failures as missing / connection / permission problems.
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode > 1:
        raise DevDbOpsError(stderr or "pg_restore failed")
    if completed.returncode == 1:
        logger.warning("dev db restore completed with warnings: %s", stderr.strip())

    return {
        "restored": name,
        "message": (
            "Database restored. Restart API/worker processes if sessions fail; "
            "ENCRYPTION_KEY must match the dump sidecar."
        ),
        "warnings": stderr.strip() or None,
    }


def _docker_container_running(docker: str, container: str) -> bool:
    completed = subprocess.run(
        [docker, "inspect", "-f", "{{.State.Running}}", container],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0 and completed.stdout.strip().lower() == "true"
