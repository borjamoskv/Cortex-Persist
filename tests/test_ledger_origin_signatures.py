# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from legacy_research.ledger.models import ActionResult, ActionTarget, LedgerEvent
from legacy_research.ledger.origin import (
    OriginKeyRecord,
    OriginKeyRegistry,
    OriginSignatureError,
    OriginSignaturePolicy,
    sign_event_origin,
    verify_event_origin,
)
from legacy_research.ledger.queue import EnrichmentQueue
from legacy_research.ledger.store import LedgerStore
from legacy_research.ledger.verifier import LedgerVerifier
from legacy_research.ledger.writer import LedgerWriter

ACTOR_ID = "agent-risk-01"
OTHER_ACTOR_ID = "agent-risk-02"
TENANT_ID = "tenant-acme"
KEY_ID = "ed25519:agent-risk-01:runtime-001"
ISSUED_AT = "2026-02-03T10:15:30Z"
NONCE = "nonce_01HXORIGIN000000000000001"


def test_strict_origin_policy_accepts_signed_authorized_event(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _strict_writer(tmp_path, private_key)
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        issued_at=ISSUED_AT,
        nonce=NONCE,
    )

    event_id = writer.append(event)

    with store.tx() as conn:
        row = conn.execute(
            "SELECT payload_json FROM ledger_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    assert row is not None
    payload = json.loads(row["payload_json"])
    assert payload["origin"]["actor_id"] == ACTOR_ID
    assert payload["origin"]["actor_key_id"] == KEY_ID
    assert payload["origin"]["tenant_id"] == TENANT_ID
    assert payload["origin"]["action"] == "fact.store"
    assert payload["origin"]["hash_alg"] == "sha256"
    assert payload["origin"]["signature_alg"] == "ed25519"
    assert payload["origin"]["nonce"] == NONCE
    assert isinstance(payload["origin"]["payload_hash"], str)
    assert LedgerVerifier(store).verify_chain()["valid"] is True


def test_strict_origin_policy_rejects_unsigned_event_before_persistence(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _strict_writer(tmp_path, private_key)

    with pytest.raises(OriginSignatureError, match="origin_signature_missing"):
        writer.append(_event())

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_strict_origin_policy_rejects_bad_signature_before_persistence(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _strict_writer(tmp_path, private_key)
    signed = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        issued_at=ISSUED_AT,
        nonce=NONCE,
    )
    assert signed.origin is not None
    bad_origin = dataclasses.replace(signed.origin, origin_signature="not-a-valid-signature")
    bad_event = dataclasses.replace(signed, origin=bad_origin)

    with pytest.raises(OriginSignatureError, match="origin_signature_invalid"):
        writer.append(bad_event)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_strict_origin_policy_rejects_actor_key_mismatch_before_persistence(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = OriginKeyRegistry(
        [
            _record(
                private_key,
                actor_id=OTHER_ACTOR_ID,
                permissions=["fact.store"],
            )
        ]
    )
    store, writer = _writer_with_registry(tmp_path, registry)
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        issued_at=ISSUED_AT,
        nonce=NONCE,
    )

    with pytest.raises(OriginSignatureError, match="origin_key_actor_mismatch"):
        writer.append(event)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_strict_origin_policy_rejects_action_not_permitted_before_persistence(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = OriginKeyRegistry(
        [_record(private_key, permissions=["fact.deprecate"], valid_from="2026-01-01T00:00:00Z")]
    )
    store, writer = _writer_with_registry(tmp_path, registry)
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        issued_at=ISSUED_AT,
        nonce=NONCE,
    )

    with pytest.raises(OriginSignatureError, match="origin_key_permission_denied:fact.store"):
        writer.append(event)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_strict_origin_policy_rejects_revoked_future_key_before_persistence(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = OriginKeyRegistry(
        [
            _record(
                private_key,
                status="revoked",
                valid_from="2026-01-01T00:00:00Z",
                valid_until="2026-02-01T00:00:00Z",
            )
        ]
    )
    store, writer = _writer_with_registry(tmp_path, registry)
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        issued_at=ISSUED_AT,
        nonce=NONCE,
    )

    with pytest.raises(OriginSignatureError, match="origin_key_expired"):
        writer.append(event)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_rotated_historical_key_verifies_for_event_within_validity_window() -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = OriginKeyRegistry(
        [
            _record(
                private_key,
                status="revoked",
                valid_from="2026-01-01T00:00:00Z",
                valid_until="2026-03-01T00:00:00Z",
            )
        ]
    )
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        issued_at=ISSUED_AT,
        nonce=NONCE,
    )

    verify_event_origin(event, registry)


def test_origin_registry_public_export_excludes_private_key_material() -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = OriginKeyRegistry([_record(private_key, permissions=["fact.store"])])

    public_registry = registry.to_public_dict()
    encoded = json.dumps(public_registry, sort_keys=True)

    assert "public_key" in encoded
    assert "private_key" not in encoded
    assert "seed" not in encoded
    assert "secret" not in encoded


def _strict_writer(
    tmp_path: Path,
    private_key: Ed25519PrivateKey,
) -> tuple[LedgerStore, LedgerWriter]:
    registry = OriginKeyRegistry([_record(private_key, permissions=["fact.store"])])
    return _writer_with_registry(tmp_path, registry)


def _writer_with_registry(
    tmp_path: Path,
    registry: OriginKeyRegistry,
) -> tuple[LedgerStore, LedgerWriter]:
    store = LedgerStore(tmp_path / "ledger.db")
    return (
        store,
        LedgerWriter(
            store,
            EnrichmentQueue(store),
            origin_policy=OriginSignaturePolicy.strict_mode(registry),
        ),
    )


def _record(
    private_key: Ed25519PrivateKey,
    *,
    permissions: list[str] | None = None,
    actor_id: str = ACTOR_ID,
    tenant_id: str = TENANT_ID,
    status: str = "active",
    valid_from: str | None = "2026-01-01T00:00:00Z",
    valid_until: str | None = "2027-01-01T00:00:00Z",
) -> OriginKeyRecord:
    return OriginKeyRecord.from_public_key(
        key_id=KEY_ID,
        actor_id=actor_id,
        tenant_id=tenant_id,
        public_key=private_key.public_key(),
        permissions=permissions or ["fact.store"],
        status=status,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def _event() -> LedgerEvent:
    return LedgerEvent.new(
        tool="agent-runtime",
        actor=ACTOR_ID,
        action="fact.store",
        target=ActionTarget(app="CORTEX", identifier="fact:001"),
        result=ActionResult(ok=True, latency_ms=12, verified=True),
        metadata={"project": "cortex-persist", "tenant_id": TENANT_ID},
    )


def _row_count(store: LedgerStore, table_name: str) -> int:
    if table_name not in {"ledger_events", "enrichment_jobs"}:
        raise ValueError(f"unsupported table: {table_name}")
    with store.tx() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])
