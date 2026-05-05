from __future__ import annotations

import hashlib
import sqlite3

import pytest

from cortex.ledger.ledger_core import SovereignLedger
from cortex.services.trust import TrustService
from cortex.utils.canonical import canonical_json


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _seal_bundle(bundle: dict) -> None:
    bundle["manifest"]["payload_sha256"] = hashlib.sha256(
        canonical_json(bundle["payload"]).encode("utf-8")
    ).hexdigest()
    bundle["bundle_sha256"] = hashlib.sha256(
        canonical_json({"manifest": bundle["manifest"], "payload": bundle["payload"]}).encode(
            "utf-8"
        )
    ).hexdigest()


def _create_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            hash TEXT,
            tx_id INTEGER
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project TEXT NOT NULL,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp REAL
        );
        CREATE TABLE merkle_roots (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            tx_id INTEGER
        );
        """
    )
    conn.executemany(
        """
        INSERT INTO facts (id, tenant_id, project, content, hash, tx_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "tenant-alpha", "proj", "alpha fact", _hash("alpha fact"), 1),
            (2, "tenant-beta", "proj", "beta fact", _hash("beta fact"), 2),
        ],
    )
    conn.executemany(
        """
        INSERT INTO transactions (id, tenant_id, project, action, detail, prev_hash, hash, timestamp)
        VALUES (?, ?, ?, 'store', '{}', '', ?, ?)
        """,
        [
            (1, "tenant-alpha", "proj", "tx-alpha", 1.0),
            (2, "tenant-beta", "proj", "tx-beta", 2.0),
        ],
    )
    conn.execute("INSERT INTO merkle_roots (id, tenant_id, tx_id) VALUES (1, 'tenant-alpha', 1)")
    conn.commit()
    conn.close()


def test_verify_fact_chain_rejects_foreign_tenant(tmp_path) -> None:
    db_path = tmp_path / "trust.db"
    _create_db(str(db_path))
    service = TrustService(str(db_path))

    with pytest.raises(ValueError, match="tenant tenant-alpha"):
        service.verify_fact_chain(2, tenant_id="tenant-alpha")

    result = service.verify_fact_chain(2, tenant_id="tenant-beta")

    assert result.valid is True


def test_verify_batch_is_tenant_scoped(tmp_path) -> None:
    db_path = tmp_path / "trust.db"
    _create_db(str(db_path))
    service = TrustService(str(db_path))

    results = service.verify_batch([1, 2], tenant_id="tenant-alpha")

    assert [item.fact_id for item in results] == [1]


def test_compliance_stats_are_tenant_scoped(tmp_path) -> None:
    db_path = tmp_path / "trust.db"
    _create_db(str(db_path))
    service = TrustService(str(db_path))

    alpha = service.get_compliance_stats(tenant_id="tenant-alpha")
    beta = service.get_compliance_stats(tenant_id="tenant-beta")

    assert alpha.total_facts == 1
    assert beta.total_facts == 1
    assert alpha.chain_integrity is True
    assert beta.chain_integrity is True


def test_compliance_stats_detect_range_merkle_gaps(tmp_path) -> None:
    db_path = tmp_path / "trust_range.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            hash TEXT,
            tx_id INTEGER
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project TEXT NOT NULL,
            action TEXT,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT,
            timestamp REAL
        );
        CREATE TABLE merkle_roots (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            root_hash TEXT NOT NULL,
            tx_start_id INTEGER NOT NULL,
            tx_end_id INTEGER NOT NULL,
            tx_count INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO facts (id, tenant_id, project, content, hash, tx_id) "
        "VALUES (1, 'tenant-alpha', 'proj', 'alpha fact', ?, 1)",
        (_hash("alpha fact"),),
    )
    conn.executemany(
        "INSERT INTO transactions "
        "(id, tenant_id, project, action, detail, prev_hash, hash, timestamp) "
        "VALUES (?, 'tenant-alpha', 'proj', 'store', '{}', '', ?, ?)",
        [(1, "tx-1", 1.0), (2, "tx-2", 2.0), (3, "tx-3", 3.0)],
    )
    conn.execute(
        "INSERT INTO merkle_roots "
        "(id, tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
        "VALUES (1, 'tenant-alpha', 'root-1', 1, 1, 1)"
    )
    conn.commit()
    conn.close()

    stats = TrustService(str(db_path)).get_compliance_stats(tenant_id="tenant-alpha")

    assert stats.chain_integrity is False
    assert any("CHAIN_GAP" in violation for violation in stats.violations)


def test_audit_trail_is_tenant_scoped(tmp_path) -> None:
    db_path = tmp_path / "trust.db"
    _create_db(str(db_path))
    service = TrustService(str(db_path))

    rows = service.get_audit_trail(tenant_id="tenant-alpha")

    assert [row["tenant_id"] for row in rows] == ["tenant-alpha"]


@pytest.mark.asyncio
async def test_siege_scan_is_tenant_scoped(tmp_path) -> None:
    db_path = tmp_path / "trust.db"
    _create_db(str(db_path))
    service = TrustService(str(db_path))

    report = await service.run_siege_scan_async(tenant_id="tenant-alpha")

    assert report["probes_performed"] == 1
    assert report["vulnerabilities_found"] == 0


def _create_verifiable_bundle_db(path: str) -> None:
    conn = sqlite3.connect(path)
    ledger = SovereignLedger(conn)
    ledger._config.CHECKPOINT_MAX = 1
    tx_hash = ledger.record_transaction(
        "proj",
        "store",
        {"fact_id": 1},
        tenant_id="tenant-alpha",
    )
    tx_id = conn.execute("SELECT id FROM transactions WHERE hash = ?", (tx_hash,)).fetchone()[0]
    conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            hash TEXT,
            tx_id INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO facts (id, tenant_id, project, content, hash, tx_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "tenant-alpha", "proj", "alpha fact", _hash("alpha fact"), tx_id),
    )
    assert ledger.create_checkpoint("tenant-alpha") is not None
    conn.commit()
    conn.close()


def test_evidence_bundle_round_trip_verifies_offline(tmp_path) -> None:
    db_path = tmp_path / "evidence.db"
    _create_verifiable_bundle_db(str(db_path))
    service = TrustService(str(db_path))

    bundle = service.export_evidence_bundle(tenant_id="tenant-alpha", project="proj")
    report = TrustService.verify_evidence_bundle(bundle)

    assert bundle["manifest"]["tenant_id"] == "tenant-alpha"
    assert bundle["manifest"]["payload_sha256"] == hashlib.sha256(
        canonical_json(bundle["payload"]).encode("utf-8")
    ).hexdigest()
    assert report == {
        "valid": True,
        "violations": [],
        "checked": {
            "facts": 1,
            "transactions": 1,
            "merkle_roots": 1,
            "causal_edges": 0,
        },
    }


def test_evidence_bundle_detects_resigned_tenant_transplant(tmp_path) -> None:
    db_path = tmp_path / "evidence.db"
    _create_verifiable_bundle_db(str(db_path))
    service = TrustService(str(db_path))
    bundle = service.export_evidence_bundle(tenant_id="tenant-alpha")
    bundle["payload"]["transactions"][0]["tenant_id"] = "tenant-beta"
    _seal_bundle(bundle)

    report = TrustService.verify_evidence_bundle(bundle)

    assert report["valid"] is False
    assert any(v["type"] == "TX_HASH_MISMATCH" for v in report["violations"])


def test_evidence_bundle_detects_manifest_rewrite(tmp_path) -> None:
    db_path = tmp_path / "evidence.db"
    _create_verifiable_bundle_db(str(db_path))
    service = TrustService(str(db_path))
    bundle = service.export_evidence_bundle(tenant_id="tenant-alpha")
    bundle["manifest"]["generated_at"] = 0

    report = TrustService.verify_evidence_bundle(bundle)

    assert report["valid"] is False
    assert any(v["type"] == "BUNDLE_HASH_MISMATCH" for v in report["violations"])


def test_evidence_bundle_detects_foreign_fact_even_when_resigned(tmp_path) -> None:
    db_path = tmp_path / "evidence.db"
    _create_verifiable_bundle_db(str(db_path))
    service = TrustService(str(db_path))
    bundle = service.export_evidence_bundle(tenant_id="tenant-alpha")
    bundle["payload"]["facts"].append(
        {
            "id": 99,
            "tenant_id": "tenant-beta",
            "project": "proj",
            "content": "foreign fact",
            "hash": _hash("foreign fact"),
            "tx_id": None,
        }
    )
    _seal_bundle(bundle)

    report = TrustService.verify_evidence_bundle(bundle)

    assert report["valid"] is False
    assert any(v["type"] == "TENANT_SCOPE_MISMATCH" for v in report["violations"])
