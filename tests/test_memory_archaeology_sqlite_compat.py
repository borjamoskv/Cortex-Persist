from __future__ import annotations

import _sqlite3
from types import SimpleNamespace

from cortex.memory.memory_archaeology import MemoryArchaeologist


class _FailingCursor:
    def execute(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise _sqlite3.Error("stdlib sqlite backend mismatch")


class _FailingConnection:
    def cursor(self) -> _FailingCursor:
        return _FailingCursor()


class _FakeL2Store:
    def _get_conn(self) -> _FailingConnection:
        return _FailingConnection()

    def _get_domain_tables(self, l2_conn, tenant_id, project):  # noqa: ANN001
        return ("meta_tb", "vec_tb", None, None)


class _FakeEngine:
    def __init__(self) -> None:
        self.memory = SimpleNamespace(_l2=_FakeL2Store(), _encoder=object())


def test_extract_vectors_handles_stdlib_sqlite_error_from_backend() -> None:
    """Regression for backend/stdlib sqlite exception mismatch in archaeology."""
    archaeologist = MemoryArchaeologist(_FakeEngine())

    facts, vecs = archaeologist._extract_vectors(
        "project-x",
        "tenant-x",
        {"1": {"id": "1", "content": "content", "parent_decision_id": None, "tenant_id": "tenant-x"}},
    )

    assert facts == []
    assert vecs is None
