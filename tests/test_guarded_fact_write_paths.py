"""Regression tests for guarded fact write paths."""

from __future__ import annotations

import re
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

from cortex.extensions.daemon.entropic_wake import EntropicWakeDaemon
from cortex.extensions.daemon.frontier import FrontierDaemon
from cortex.extensions.daemon.zero_prompting import ZeroPromptingDaemon
from cortex.extensions.gate.ouroboros import OuroborosGate


class RecordingEngine:
    def __init__(self) -> None:
        self.store_calls: list[dict[str, Any]] = []

    async def store(self, **kwargs: Any) -> int:
        self.store_calls.append(kwargs)
        return len(self.store_calls)


class RecordingOuroborosEngine(RecordingEngine):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn
        self.invalidations: list[tuple[int, str, str | None]] = []

    def _get_sync_conn(self) -> sqlite3.Connection:
        return self.conn

    async def invalidate(
        self,
        fact_id: int,
        reason: str | None = None,
        tenant_id: str = "default",
    ) -> bool:
        self.invalidations.append((fact_id, tenant_id, reason))
        return True


class AsyncRowsCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows

    async def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows


class AsyncSelectConnection:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows
        self.statements: list[str] = []

    async def execute(self, statement: str, params: tuple[Any, ...] = ()) -> AsyncRowsCursor:
        self.statements.append(statement)
        return AsyncRowsCursor(self.rows)


class PurgeRecordingEngine:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.conn = AsyncSelectConnection(rows)
        self.purge_calls: list[tuple[int, str, bool]] = []

    @asynccontextmanager
    async def session(self) -> Any:
        yield self.conn

    async def purge(
        self,
        fact_id: int,
        tenant_id: str = "default",
        force: bool = False,
    ) -> bool:
        self.purge_calls.append((fact_id, tenant_id, force))
        return True


@pytest.mark.asyncio
async def test_daemon_logs_use_guarded_store() -> None:
    engine = RecordingEngine()

    await FrontierDaemon(engine=engine)._log_evolution("ingestion", "read source")
    await ZeroPromptingDaemon(engine=engine, workspace_root=".")._crystallize(
        "hypothesis",
        {"action": "scan", "success": True},
        {"net_positive": True},
    )
    await EntropicWakeDaemon(engine=engine)._log_action_to_cortex("module")

    assert [call["source"] for call in engine.store_calls] == [
        "daemon:frontier",
        "daemon:zero-prompting",
        "daemon:entropic-wake",
    ]
    assert {call["tenant_id"] for call in engine.store_calls} == {"system"}
    assert all(call["fact_type"] == "decision" for call in engine.store_calls)


def test_ouroboros_pruning_uses_guarded_invalidations() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT,
            project TEXT,
            is_tombstoned INTEGER DEFAULT 0
        )
        """
    )
    conn.executemany(
        "INSERT INTO facts (id, tenant_id, project) VALUES (?, ?, ?)",
        [(1, "alpha", "dead"), (2, "beta", "dead"), (3, "alpha", "live")],
    )

    engine = RecordingOuroborosEngine(conn)
    gate = OuroborosGate(engine)

    pruned = gate.trigger_pruning("dead")

    assert pruned == 2
    assert engine.invalidations == [
        (1, "alpha", "ouroboros_pruned_project:dead"),
        (2, "beta", "ouroboros_pruned_project:dead"),
    ]
    assert conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'dead'").fetchone()[0] == 2
    assert engine.store_calls[0]["source"] == "ag:ouroboros"


@pytest.mark.asyncio
async def test_gc_delegates_physical_fact_deletion_to_canonical_purge() -> None:
    from cortex.compaction.gc import GarbageCollector

    engine = PurgeRecordingEngine([(10, "alpha"), (11, None)])
    gc = GarbageCollector(engine)

    stats = await gc.run_gc(batch_size=2, force=True)

    assert stats["status"] == "completed"
    assert stats["deleted_facts"] == 2
    assert engine.purge_calls == [(10, "alpha", True), (11, "default", True)]
    assert all("DELETE FROM FACTS" not in stmt.upper() for stmt in engine.conn.statements)


@pytest.mark.asyncio
async def test_inference_persistence_requires_guarded_storer() -> None:
    from cortex.engine.inference import Derivation, InferenceEngine

    derivation = Derivation(
        content="derived",
        project="p",
        source_fact_ids=[1],
        rule_name="rule",
    )

    with pytest.raises(RuntimeError, match="guarded storer"):
        await InferenceEngine()._persist_derivations(None, [derivation], "tenant")


def test_runtime_fact_inserts_stay_in_canonical_store_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    canonical = repo_root / "cortex" / "engine" / "fact_store_core.py"
    pattern = re.compile(r"\bINSERT\s+INTO\s+facts\b", re.IGNORECASE)

    offenders: list[str] = []
    for path in (repo_root / "cortex").rglob("*.py"):
        if path == canonical:
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(path.relative_to(repo_root).as_posix())

    assert offenders == []


def test_runtime_fact_deletes_stay_in_canonical_purge_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    canonical = repo_root / "cortex" / "engine" / "store_mutation.py"
    pattern = re.compile(r"\bDELETE\s+FROM\s+facts\b", re.IGNORECASE)

    offenders: list[str] = []
    for path in (repo_root / "cortex").rglob("*.py"):
        if path == canonical:
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(path.relative_to(repo_root).as_posix())

    assert offenders == []


def test_state_changing_fact_updates_stay_in_mutation_gateway() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    allowed = {
        "cortex/engine/mutation_engine.py",
        "cortex/engine/store_mutation.py",
    }
    state_columns = (
        "confidence",
        "valid_until",
        "fact_type",
        "is_tombstoned",
        "is_quarantined",
        "consensus_score",
    )

    offenders: list[str] = []
    for path in (repo_root / "cortex").rglob("*.py"):
        rel = path.relative_to(repo_root).as_posix()
        if rel in allowed or rel.startswith("cortex/migrations/"):
            continue
        text = path.read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", text).lower()
        if "update facts set" in normalized and any(
            f"update facts set {column}" in normalized for column in state_columns
        ):
            offenders.append(rel)

    assert offenders == []
