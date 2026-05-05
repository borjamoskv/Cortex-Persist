from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.pii import LedgerPIIError, LedgerPIIPolicy, scrub_text
from cortex.ledger.public_export import ExportAuthority, write_public_ledger_export
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.writer import LedgerWriter


def test_pii_policy_rejects_email_before_ledger_persistence(tmp_path: Path) -> None:
    store, writer = _writer(tmp_path)
    event = _event(target=ActionTarget(app="CORTEX", title="alice@example.com"))

    with pytest.raises(LedgerPIIError) as exc:
        writer.append(event)

    assert "alice@example.com" not in str(exc.value)
    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_pii_policy_rejects_non_allowlisted_metadata_key(tmp_path: Path) -> None:
    store, writer = _writer(tmp_path)
    event = _event(metadata={"project": "cortex-persist", "email": "redacted-ref"})

    with pytest.raises(LedgerPIIError, match="ledger_forbidden_identifier_key"):
        writer.append(event)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_pii_policy_accepts_allowlisted_references(tmp_path: Path) -> None:
    store, writer = _writer(tmp_path)
    event = _event(
        metadata={
            "payload_ref": "blob:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "project": "cortex-persist",
            "subject_ref": "subject:hmac-sha256:01HX",
            "tenant_id": "tenant-acme",
        }
    )

    event_id = writer.append(event)

    assert isinstance(event_id, str)
    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "enrichment_jobs") == 1


def test_scrub_text_removes_direct_identifiers() -> None:
    scrubbed = scrub_text("Operator note: alice@example.com / +34600111222 / 123-45-6789")

    assert "alice@example.com" not in scrubbed
    assert "+34600111222" not in scrubbed
    assert "123-45-6789" not in scrubbed
    assert scrubbed.count("[REDACTED]") == 3


def test_public_ledger_export_rejects_direct_identifier_without_echo(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    event = {
        "detail": {"fact_type": "decision", "subject_ref": "alice@example.com"},
        "event_id": "evt-pii-001",
        "hash": "abc",
        "prev_hash": "GENESIS",
        "recorded_at": "2026-02-03T10:15:30Z",
        "sequence": 1,
        "stream_id": "tenant:acme:ledger:primary",
        "tenant_id": "tenant-acme",
    }

    with pytest.raises(ValueError) as exc:
        write_public_ledger_export(
            events=[event],
            export_dir=tmp_path / "export",
            public_keys=[],
            export_authority=ExportAuthority(
                key_id="ed25519:export:test",
                actor_id="export-authority-01",
                private_key=private_key,
            ),
            export_id="export-pii-001",
            tenant_id="tenant-acme",
            stream_id="tenant:acme:ledger:primary",
            created_at="2026-02-03T10:15:30Z",
        )

    assert "alice@example.com" not in str(exc.value)


def _writer(tmp_path: Path) -> tuple[LedgerStore, LedgerWriter]:
    store = LedgerStore(tmp_path / "ledger.db")
    return store, LedgerWriter(store, EnrichmentQueue(store), pii_policy=LedgerPIIPolicy())


def _event(
    *,
    target: ActionTarget | None = None,
    metadata: dict[str, object] | None = None,
) -> LedgerEvent:
    return LedgerEvent.new(
        tool="agent-runtime",
        actor="agent-risk-01",
        action="fact.store",
        target=target or ActionTarget(app="CORTEX", identifier="fact:001"),
        result=ActionResult(ok=True, latency_ms=12, verified=True),
        metadata=metadata or {"project": "cortex-persist", "tenant_id": "tenant-acme"},
    )


def _row_count(store: LedgerStore, table_name: str) -> int:
    if table_name not in {"ledger_events", "enrichment_jobs"}:
        raise ValueError(f"unsupported table: {table_name}")
    with store.tx() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])
