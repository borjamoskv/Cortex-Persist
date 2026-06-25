# [C5-REAL] Exergy-Maximized
from __future__ import annotations




import dataclasses
import json
import shutil
import sqlite3

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from legacy_research.ledger.models import ActionResult, ActionTarget, LedgerEvent
from legacy_research.ledger.origin import OriginKeyRecord, OriginKeyRegistry, OriginSignaturePolicy
from legacy_research.ledger.queue import EnrichmentQueue
from legacy_research.ledger.replay import (
    ReplayAdmissionError,
    ReplayAdmissionPolicy,
    validate_batch_import_manifest,
)
from legacy_research.ledger.store import LedgerStore
from legacy_research.ledger.writer import LedgerWriter



ACTOR_ID = "agent-risk-01"
TENANT_ID = "tenant-acme"
OTHER_TENANT_ID = "tenant-beta"
KEY_ID = "ed25519:agent-risk-01:runtime-001"
OTHER_KEY_ID = "ed25519:agent-risk-01:runtime-002"
NOW = datetime(2026, 2, 3, 10, 15, 30, tzinfo=timezone.utc)
ISSUED_AT = "2026-02-03T10:15:30Z"
FIXTURES = Path(__file__).parent / "fixtures" / "ledger_verifier"
STRICT = FIXTURES / "public_v1_strict"


def test_replay_admission_records_reservation_atomically_with_ledger_write(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    event = _signed_event(private_key, event_id="evt-001", nonce="nonce-001")

    event_id = writer.append(event)

    assert event_id == "evt-001"
    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "enrichment_jobs") == 1
    with store.tx() as conn:
        row = conn.execute(
            """
            SELECT tenant_id, event_id, nonce, payload_hash, actor_key_id, action
            FROM ledger_replay_admissions
            """
        ).fetchone()
    assert dict(row) == {
        "tenant_id": TENANT_ID,
        "event_id": "evt-001",
        "nonce": "nonce-001",
        "payload_hash": event.origin.payload_hash if event.origin else "",
        "actor_key_id": KEY_ID,
        "action": "fact.store",
    }


def test_duplicate_event_id_rejected_without_consuming_new_nonce(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    writer.append(_signed_event(private_key, event_id="evt-001", nonce="nonce-001"))
    duplicate = _signed_event(private_key, event_id="evt-001", nonce="nonce-002")

    with pytest.raises(ReplayAdmissionError, match="replay_event_id_duplicate"):
        writer.append(duplicate)

    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "enrichment_jobs") == 1
    assert _row_count(store, "ledger_replay_admissions") == 1


def test_duplicate_nonce_rejected_without_consuming_new_event_id(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    writer.append(_signed_event(private_key, event_id="evt-001", nonce="nonce-001"))
    duplicate = _signed_event(private_key, event_id="evt-002", nonce="nonce-001")

    with pytest.raises(ReplayAdmissionError, match="replay_nonce_duplicate"):
        writer.append(duplicate)

    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "enrichment_jobs") == 1
    assert _row_count(store, "ledger_replay_admissions") == 1


def test_mutated_retry_rejected_but_exact_retry_is_idempotent(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key, permissions=["fact.store", "fact.deprecate"])
    event = _signed_event(private_key, event_id="evt-001", nonce="nonce-001")
    first = writer.append(event)

    exact_retry = writer.append(event)

    assert exact_retry == first
    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "enrichment_jobs") == 1
    assert _row_count(store, "ledger_replay_admissions") == 1

    mutated = _signed_event(
        private_key,
        event_id="evt-001",
        nonce="nonce-001",
        action="fact.deprecate",
    )
    with pytest.raises(ReplayAdmissionError, match="replay_retry_mutated"):
        writer.append(mutated)

    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "enrichment_jobs") == 1
    assert _row_count(store, "ledger_replay_admissions") == 1


def test_online_freshness_rejects_future_and_stale_events_before_reservation(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)

    future = _signed_event(
        private_key,
        event_id="evt-future",
        nonce="nonce-future",
        issued_at="2026-02-03T10:17:00Z",
    )
    with pytest.raises(ReplayAdmissionError, match="online_freshness_future_event"):
        writer.append(future)

    stale = _signed_event(
        private_key,
        event_id="evt-stale",
        nonce="nonce-stale",
        issued_at="2026-02-03T10:00:00Z",
    )
    with pytest.raises(ReplayAdmissionError, match="online_freshness_stale_event"):
        writer.append(stale)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0
    assert _row_count(store, "ledger_replay_admissions") == 0


def test_replay_constraints_are_tenant_scoped_for_event_ids_and_nonces(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "ledger.db")

    with store.tx() as conn:
        _insert_admission(conn, tenant_id=TENANT_ID, event_id="evt-shared", nonce="nonce-shared")
        _insert_admission(
            conn,
            tenant_id=OTHER_TENANT_ID,
            event_id="evt-shared",
            nonce="nonce-shared",
        )
        count = conn.execute("SELECT COUNT(*) AS count FROM ledger_replay_admissions").fetchone()

    assert count["count"] == 2


def test_batch_import_without_manifest_is_rejected_but_offline_verify_stays_limited(
    tmp_path: Path,
) -> None:
    from legacy_research.ledger.public_verifier import verify_export

    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    (export_dir / "manifest.json").unlink()

    offline_report = verify_export(export_dir)
    assert offline_report["result"] == "VALID_WITH_LIMITATIONS"
    with pytest.raises(ReplayAdmissionError, match="batch_import_manifest_missing"):
        validate_batch_import_manifest(export_dir)


def test_concurrent_duplicate_nonce_has_one_accept_and_one_deterministic_reject(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    events = [
        _signed_event(private_key, event_id="evt-001", nonce="nonce-race"),
        _signed_event(private_key, event_id="evt-002", nonce="nonce-race"),
    ]

    def submit(event: LedgerEvent) -> tuple[str, str]:
        try:
            return ("accepted", writer.append(event))
        except ReplayAdmissionError as exc:
            return ("rejected", str(exc))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, events))

    accepted = [value for status, value in results if status == "accepted"]
    rejected = [value for status, value in results if status == "rejected"]
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0].startswith(f"replay_nonce_duplicate:{TENANT_ID}:nonce-race")
    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "enrichment_jobs") == 1
    assert _row_count(store, "ledger_replay_admissions") == 1


def test_legacy_ledger_store_upgrade_adds_replay_table_without_data_loss(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-ledger.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE ledger_events (
            event_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            tool TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            prev_hash TEXT,
            hash TEXT,
            semantic_status TEXT NOT NULL DEFAULT 'pending',
            semantic_error TEXT,
            correlation_id TEXT,
            trace_id TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        INSERT INTO ledger_events (
            event_id, ts, tool, actor, action, payload_json, semantic_status
        )
        VALUES ('legacy-evt', '2026-01-01T00:00:00Z', 'cli', 'legacy', 'fact.store', '{}', 'pending');
    """)
    conn.commit()
    conn.close()

    store = LedgerStore(db_path)

    with store.tx() as upgraded:
        legacy = upgraded.execute(
            "SELECT event_id FROM ledger_events WHERE event_id = 'legacy-evt'"
        ).fetchone()
        replay_columns = {
            row[1] for row in upgraded.execute("PRAGMA table_info(ledger_replay_admissions)")
        }
    assert legacy is not None
    assert {"tenant_id", "event_id", "nonce", "request_hash"} <= replay_columns


def _writer(
    tmp_path: Path,
    private_key: Ed25519PrivateKey,
    *,
    permissions: list[str] | None = None,
) -> tuple[LedgerStore, LedgerWriter]:
    store = LedgerStore(tmp_path / "ledger.db")
    registry = OriginKeyRegistry(
        [
            _record(
                private_key,
                key_id=KEY_ID,
                tenant_id=TENANT_ID,
                permissions=permissions or ["fact.store"],
            )
        ]
    )
    return (
        store,
        LedgerWriter(
            store,
            EnrichmentQueue(store),
            origin_policy=OriginSignaturePolicy.strict_mode(registry),
            replay_policy=ReplayAdmissionPolicy(now=lambda: NOW),
        ),
    )


def _record(
    private_key: Ed25519PrivateKey,
    *,
    key_id: str,
    tenant_id: str,
    permissions: list[str],
) -> OriginKeyRecord:
    return OriginKeyRecord.from_public_key(
        key_id=key_id,
        actor_id=ACTOR_ID,
        tenant_id=tenant_id,
        public_key=private_key.public_key(),
        permissions=permissions,
        valid_from="2026-01-01T00:00:00Z",
        valid_until="2027-01-01T00:00:00Z",
    )


def _signed_event(
    private_key: Ed25519PrivateKey,
    *,
    event_id: str,
    nonce: str,
    tenant_id: str = TENANT_ID,
    key_id: str = KEY_ID,
    action: str = "fact.store",
    issued_at: str = ISSUED_AT,
) -> LedgerEvent:
    from legacy_research.ledger.origin import sign_event_origin

    event = LedgerEvent.new(
        tool="agent-runtime",
        actor=ACTOR_ID,
        action=action,
        target=ActionTarget(app="CORTEX", identifier=event_id),
        result=ActionResult(ok=True, latency_ms=12, verified=True),
        metadata={"project": "cortex-persist", "tenant_id": tenant_id},
    )
    event = dataclasses.replace(event, event_id=event_id)
    return sign_event_origin(
        event,
        key_id=key_id,
        private_key=private_key,
        tenant_id=tenant_id,
        issued_at=issued_at,
        nonce=nonce,
    )


def _insert_admission(
    conn: sqlite3.Connection,
    *,
    tenant_id: str,
    event_id: str,
    nonce: str,
) -> None:
    conn.execute(
        """
        INSERT INTO ledger_replay_admissions (
            tenant_id,
            event_id,
            nonce,
            request_hash,
            payload_hash,
            ledger_event_id,
            actor_key_id,
            action,
            issued_at,
            accepted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            event_id,
            nonce,
            f"request:{tenant_id}",
            f"payload:{tenant_id}",
            event_id,
            f"key:{tenant_id}",
            "fact.store",
            ISSUED_AT,
            ISSUED_AT,
        ),
    )


def _row_count(store: LedgerStore, table_name: str) -> int:
    if table_name not in {"ledger_events", "enrichment_jobs", "ledger_replay_admissions"}:
        raise ValueError(f"unsupported table: {table_name}")
    with store.tx() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])
