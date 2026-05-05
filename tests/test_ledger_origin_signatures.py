from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.origin import (
    OriginKeyRecord,
    OriginKeyRegistry,
    OriginSignatureError,
    OriginSignaturePolicy,
    sign_event_origin,
    verify_event_origin,
)
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier
from cortex.ledger.writer import LedgerWriter

ACTOR_ID = "agent-risk-01"
KEY_ID = "ed25519:agent-risk-01:runtime-001"
SIGNED_AT = "2026-02-03T10:15:30Z"
NONCE = "nonce_01HXORIGIN000000000000001"


def test_strict_origin_policy_accepts_signed_authorized_event(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _strict_writer(tmp_path, private_key)
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        signed_at=SIGNED_AT,
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
    assert payload["origin"]["key_id"] == KEY_ID
    assert payload["origin"]["signature_alg"] == "ed25519"
    assert payload["origin"]["nonce"] == NONCE
    assert LedgerVerifier(store).verify_chain()["valid"] is True


def test_strict_origin_policy_rejects_unsigned_event_before_persistence(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _strict_writer(tmp_path, private_key)

    with pytest.raises(OriginSignatureError, match="origin_signature_missing"):
        writer.append(_event())

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_strict_origin_policy_rejects_tampered_event_before_persistence(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _strict_writer(tmp_path, private_key)
    signed = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        signed_at=SIGNED_AT,
        nonce=NONCE,
    )
    tampered = dataclasses.replace(signed, target=ActionTarget(app="Tampered"))

    with pytest.raises(OriginSignatureError, match="origin_signature_invalid"):
        writer.append(tampered)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_strict_origin_policy_rejects_permission_denied_before_persistence(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = OriginKeyRegistry(
        [
            OriginKeyRecord.from_public_key(
                key_id=KEY_ID,
                actor_id=ACTOR_ID,
                public_key=private_key.public_key(),
                permissions=["fact.read"],
            )
        ]
    )
    store = LedgerStore(tmp_path / "ledger.db")
    writer = LedgerWriter(
        store,
        EnrichmentQueue(store),
        origin_policy=OriginSignaturePolicy.strict_mode(registry),
    )
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        signed_at=SIGNED_AT,
        nonce=NONCE,
    )

    with pytest.raises(OriginSignatureError, match="origin_key_permission_denied"):
        writer.append(event)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_origin_signature_scope_verifies_independently() -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = OriginKeyRegistry(
        [
            OriginKeyRecord.from_public_key(
                key_id=KEY_ID,
                actor_id=ACTOR_ID,
                public_key=private_key.public_key(),
                permissions=["fact.store"],
            )
        ]
    )
    event = sign_event_origin(
        _event(),
        key_id=KEY_ID,
        private_key=private_key,
        signed_at=SIGNED_AT,
        nonce=NONCE,
    )

    verify_event_origin(event, registry)


def _strict_writer(
    tmp_path: Path,
    private_key: Ed25519PrivateKey,
) -> tuple[LedgerStore, LedgerWriter]:
    registry = OriginKeyRegistry(
        [
            OriginKeyRecord.from_public_key(
                key_id=KEY_ID,
                actor_id=ACTOR_ID,
                public_key=private_key.public_key(),
                permissions=["fact.store"],
            )
        ]
    )
    store = LedgerStore(tmp_path / "ledger.db")
    return (
        store,
        LedgerWriter(
            store,
            EnrichmentQueue(store),
            origin_policy=OriginSignaturePolicy.strict_mode(registry),
        ),
    )


def _event() -> LedgerEvent:
    return LedgerEvent.new(
        tool="agent-runtime",
        actor=ACTOR_ID,
        action="fact.store",
        target=ActionTarget(app="CORTEX", identifier="fact:001"),
        result=ActionResult(ok=True, latency_ms=12, verified=True),
        metadata={"project": "cortex-persist", "tenant_id": "tenant-acme"},
    )


def _row_count(store: LedgerStore, table_name: str) -> int:
    if table_name not in {"ledger_events", "enrichment_jobs"}:
        raise ValueError(f"unsupported table: {table_name}")
    with store.tx() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])
