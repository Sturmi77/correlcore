"""Unit tests for development DB dump/restore guards."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.services.dev_db_service import (
    DevDbOpsError,
    list_backups,
    require_dev_db_ops_allowed,
    restore_backup,
)


@pytest.fixture(autouse=True)
def _env(tmp_path: Path):
    original = {
        "APP_ENV": settings.APP_ENV,
        "DEV_DB_BACKUP_DIR": settings.DEV_DB_BACKUP_DIR,
        "DATABASE_URL": settings.DATABASE_URL,
    }
    settings.APP_ENV = "development"
    settings.DEV_DB_BACKUP_DIR = str(tmp_path)
    settings.DATABASE_URL = "postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore"
    yield
    for key, value in original.items():
        setattr(settings, key, value)


def test_require_dev_db_ops_rejects_production() -> None:
    settings.APP_ENV = "production"
    with pytest.raises(DevDbOpsError):
        require_dev_db_ops_allowed()


def test_list_backups_empty(tmp_path: Path) -> None:
    items, directory = list_backups()
    assert items == []
    assert directory == str(tmp_path.resolve())


def test_restore_requires_confirm() -> None:
    with pytest.raises(DevDbOpsError, match="confirm"):
        restore_backup("correlcore-dev-20260713T120000Z.dump", confirm=False)


def test_restore_rejects_unsafe_name() -> None:
    with pytest.raises(DevDbOpsError, match="Invalid"):
        restore_backup("../etc/passwd", confirm=True)


def test_list_backups_reads_sidecar(tmp_path: Path) -> None:
    dump = tmp_path / "correlcore-dev-20260713T120000Z.dump"
    dump.write_bytes(b"PGDUMP")
    dump.with_suffix(".dump.meta.json").write_text('{"ops_ready": false}\n', encoding="utf-8")
    with patch("app.services.dev_db_service._backup_dir", return_value=tmp_path):
        items, _ = list_backups()
    assert len(items) == 1
    assert items[0]["name"] == dump.name
    assert items[0]["meta"]["ops_ready"] is False
