"""Role handling for the revision-049 cross-user backfill."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from migrations import marker_tag_backfill_049 as backfill


class _Result:
    def __init__(self, *, scalar: bool | None = None, rows: list[object] | None = None) -> None:
        self._scalar = scalar
        self._rows = rows or []

    def scalar_one(self) -> bool:
        assert self._scalar is not None
        return self._scalar

    def all(self) -> list[object]:
        return self._rows


class _Connection:
    def __init__(self, *, privileged: bool, rows: list[object] | None = None) -> None:
        self.privileged = privileged
        self.rows = rows or []
        self.statements: list[str] = []

    def execute(self, statement: object) -> _Result:
        sql = str(statement)
        self.statements.append(sql)
        if "FROM pg_roles" in sql:
            return _Result(scalar=self.privileged)
        if "FROM pg_class" in sql:
            return _Result(rows=self.rows)
        return _Result()


def _owned_rows(*, forced: set[str] | None = None) -> list[object]:
    forced = forced or set()
    return [
        SimpleNamespace(relname=name, owned=True, relforcerowsecurity=name in forced)
        for name in backfill._RLS_TABLES
    ]


def test_privileged_role_keeps_force_rls_unchanged() -> None:
    conn = _Connection(privileged=True)

    assert backfill._prepare_owner_rls_access(conn) == ()
    assert not any("ALTER TABLE" in statement for statement in conn.statements)


def test_schema_owner_temporarily_unforces_only_forced_tables() -> None:
    conn = _Connection(privileged=False, rows=_owned_rows(forced={"entries", "tags"}))

    changed = backfill._prepare_owner_rls_access(conn)
    backfill._restore_forced_rls(conn, changed)

    assert changed == ("entries", "tags")
    assert "ALTER TABLE entries NO FORCE ROW LEVEL SECURITY" in conn.statements
    assert "ALTER TABLE tags NO FORCE ROW LEVEL SECURITY" in conn.statements
    assert "ALTER TABLE entries FORCE ROW LEVEL SECURITY" in conn.statements
    assert "ALTER TABLE tags FORCE ROW LEVEL SECURITY" in conn.statements


def test_restricted_non_owner_is_rejected() -> None:
    rows = _owned_rows()
    rows[0] = SimpleNamespace(
        relname=backfill._RLS_TABLES[0], owned=False, relforcerowsecurity=True
    )
    conn = _Connection(privileged=False, rows=rows)

    with pytest.raises(RuntimeError, match="not owned: entries"):
        backfill._prepare_owner_rls_access(conn)
