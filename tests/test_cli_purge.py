from __future__ import annotations

from click.testing import CliRunner

from cortex.cli.purge import purge_duplicates, purge_empty, purge_project


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows_by_call):
        self.rows_by_call = list(rows_by_call)
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        rows = self.rows_by_call.pop(0) if self.rows_by_call else []
        return _FakeCursor(rows)

    def commit(self):
        return None


class _FakeEngine:
    def __init__(self, conn):
        self.conn = conn

    def _get_sync_conn(self):
        return self.conn

    def close_sync(self):
        return None


def test_purge_duplicates_scopes_queries_to_tenant(monkeypatch) -> None:
    conn = _FakeConn([[]])
    monkeypatch.setattr("cortex.cli.purge.get_engine", lambda db: _FakeEngine(conn))

    result = CliRunner().invoke(purge_duplicates, ["--dry-run", "--tenant-id", "tenant-a"])

    assert result.exit_code == 0
    assert conn.calls
    sql, params = conn.calls[0]
    assert "COALESCE(tenant_id, 'default') = ?" in sql
    assert params == ("tenant-a",)


def test_purge_empty_scopes_queries_to_tenant(monkeypatch) -> None:
    conn = _FakeConn([[], [], [], [], []])
    monkeypatch.setattr("cortex.cli.purge.get_engine", lambda db: _FakeEngine(conn))

    result = CliRunner().invoke(purge_empty, ["--dry-run", "--tenant-id", "tenant-a"])

    assert result.exit_code == 0
    assert conn.calls
    assert all("COALESCE(tenant_id, 'default') = ?" in sql for sql, _ in conn.calls)
    assert all(params[-1] == "tenant-a" for _, params in conn.calls)


def test_purge_project_scopes_queries_to_tenant(monkeypatch) -> None:
    conn = _FakeConn([[]])
    monkeypatch.setattr("cortex.cli.purge.get_engine", lambda db: _FakeEngine(conn))

    result = CliRunner().invoke(
        purge_project,
        ["demo", "--dry-run", "--tenant-id", "tenant-a"],
    )

    assert result.exit_code == 0
    sql, params = conn.calls[0]
    assert "COALESCE(tenant_id, 'default') = ?" in sql
    assert params == ("demo", "tenant-a")
