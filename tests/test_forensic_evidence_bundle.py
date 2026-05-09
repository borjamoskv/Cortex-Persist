from __future__ import annotations

import json
import sqlite3

import aiosqlite
import pytest

from cortex.forensics.evidence_bundle import (
    EVIDENCE_COMMIT_ACTION,
    build_evidence_manifest,
    canonical_json_bytes,
    commit_evidence_manifest,
    sha256_hex,
    verify_evidence_commit,
    verify_evidence_manifest,
)
from cortex.ledger import SovereignLedger
from cortex.utils.canonical import canonical_json, compute_tx_hash, now_iso

FIXED_TS = "2026-05-05T00:00:00+00:00"


def _artifacts() -> dict[str, bytes]:
    return {
        "reports/summary.txt": b"customer secret evidence\n",
        "traces/run.json": b'{"ok":true,"steps":3}',
    }


def _manifest(tenant_id: str = "tenant-a") -> dict[str, object]:
    return build_evidence_manifest(
        _artifacts(),
        bundle_id="bundle-001",
        tenant_id=tenant_id,
        project="audit-pack",
        generated_at=FIXED_TS,
    )


def _rehash_manifest(manifest: dict[str, object]) -> None:
    body = dict(manifest)
    body.pop("manifest_sha256", None)
    manifest["manifest_sha256"] = sha256_hex(canonical_json_bytes(body))


def _insert_legacy_tx(
    conn: sqlite3.Connection,
    *,
    project: str,
    action: str = "store",
    detail: dict[str, object] | None = None,
    tenant_id: str = "default",
) -> None:
    detail_json = canonical_json(detail or {})
    timestamp = now_iso()
    row = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = row[0] if row else "GENESIS"
    tx_hash = compute_tx_hash(prev_hash, project, action, detail_json, timestamp)
    conn.execute(
        "INSERT INTO transactions (tenant_id, project, action, detail, prev_hash, hash, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tenant_id, project, action, detail_json, prev_hash, tx_hash, timestamp),
    )
    conn.commit()


def test_manifest_is_deterministic_and_rejects_tampered_artifacts() -> None:
    manifest = _manifest()
    reordered = {
        "traces/run.json": _artifacts()["traces/run.json"],
        "reports/summary.txt": _artifacts()["reports/summary.txt"],
    }

    same_manifest = build_evidence_manifest(
        reordered,
        bundle_id="bundle-001",
        tenant_id="tenant-a",
        project="audit-pack",
        generated_at=FIXED_TS,
    )
    assert same_manifest["manifest_sha256"] == manifest["manifest_sha256"]

    report = verify_evidence_manifest(manifest, {"reports/summary.txt": b"tampered"})
    assert report["valid"] is False
    violation_types = {violation["type"] for violation in report["violations"]}
    assert "ARTIFACT_HASH_MISMATCH" in violation_types
    assert "ARTIFACT_MISSING" in violation_types


@pytest.mark.parametrize("path", ["/abs.txt", "../secret.txt", "a/../b.txt", "a\\b.txt", ""])
def test_manifest_rejects_unsafe_artifact_paths(path: str) -> None:
    with pytest.raises(ValueError):
        build_evidence_manifest(
            {path: b"x"},
            bundle_id="bundle-001",
            tenant_id="tenant-a",
            generated_at=FIXED_TS,
        )


def test_commit_manifest_is_idempotent_raw_free_and_tenant_bound(tmp_path) -> None:
    db_path = str(tmp_path / "ledger.db")
    manifest = _manifest()

    first = commit_evidence_manifest(db_path, manifest, _artifacts())
    second = commit_evidence_manifest(db_path, manifest, _artifacts())

    assert first["valid"] is True
    assert first["committed"] is True
    assert first["already_committed"] is False
    assert second["already_committed"] is True
    assert second["tx_id"] == first["tx_id"]
    assert second["tx_hash"] == first["tx_hash"]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT tenant_id, action, detail, prev_hash, hash, timestamp FROM transactions"
    ).fetchone()
    conn.close()

    assert row["tenant_id"] == "tenant-a"
    assert row["action"] == EVIDENCE_COMMIT_ACTION
    assert "customer secret evidence" not in row["detail"]

    tenant_hash = compute_tx_hash(
        row["prev_hash"],
        "audit-pack",
        EVIDENCE_COMMIT_ACTION,
        row["detail"],
        row["timestamp"],
        tenant_id="tenant-a",
    )
    legacy_hash = compute_tx_hash(
        row["prev_hash"],
        "audit-pack",
        EVIDENCE_COMMIT_ACTION,
        row["detail"],
        row["timestamp"],
    )
    assert row["hash"] == tenant_hash
    assert row["hash"] != legacy_hash


def test_commit_manifest_does_not_write_when_manifest_fails(tmp_path) -> None:
    db_path = tmp_path / "ledger.db"
    manifest = _manifest()
    manifest["manifest_sha256"] = "bad"

    result = commit_evidence_manifest(str(db_path), manifest, _artifacts())

    assert result["valid"] is False
    assert result["committed"] is False
    assert not db_path.exists()


def test_commit_manifest_returns_json_status_for_structurally_invalid_manifest(tmp_path) -> None:
    db_path = tmp_path / "ledger.db"
    manifest = _manifest()
    manifest["tenant_id"] = ""
    _rehash_manifest(manifest)

    result = commit_evidence_manifest(str(db_path), manifest, _artifacts())

    assert result["valid"] is False
    assert result["committed"] is False
    assert result["violations"][0]["type"] == "COMMIT_DETAIL_INVALID"
    assert not db_path.exists()


def test_verify_commit_returns_json_status_for_structurally_invalid_manifest(tmp_path) -> None:
    db_path = tmp_path / "ledger.db"
    manifest = _manifest()
    manifest["bundle_id"] = ""
    _rehash_manifest(manifest)

    result = verify_evidence_commit(str(db_path), manifest, _artifacts())

    assert result["valid"] is False
    violation_types = {violation["type"] for violation in result["violations"]}
    assert "COMMIT_DETAIL_INVALID" in violation_types


def test_verify_commit_detects_missing_and_tampered_commit(tmp_path) -> None:
    db_path = str(tmp_path / "ledger.db")
    manifest = _manifest()

    missing = verify_evidence_commit(db_path, manifest, _artifacts())
    assert missing["valid"] is False
    assert {violation["type"] for violation in missing["violations"]} == {"COMMIT_MISSING"}

    commit_result = commit_evidence_manifest(db_path, manifest, _artifacts())
    assert commit_result["committed"] is True

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id, detail FROM transactions").fetchone()
    detail = json.loads(row["detail"])
    detail["total_bytes"] = 999
    conn.execute(
        "UPDATE transactions SET detail = ? WHERE id = ?",
        (canonical_json(detail), row["id"]),
    )
    conn.commit()
    conn.close()

    tampered = verify_evidence_commit(db_path, manifest, _artifacts())
    assert tampered["valid"] is False
    violation_types = {violation["type"] for violation in tampered["violations"]}
    assert "COMMIT_DETAIL_MISMATCH" in violation_types
    assert "TAMPER_DETECTED" in violation_types


def test_repeated_commit_fails_closed_if_existing_commit_is_corrupted(tmp_path) -> None:
    db_path = str(tmp_path / "ledger.db")
    manifest = _manifest()
    commit_result = commit_evidence_manifest(db_path, manifest, _artifacts())
    assert commit_result["committed"] is True

    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE transactions SET prev_hash = 'CORRUPTED'")
    conn.commit()
    conn.close()

    repeated = commit_evidence_manifest(db_path, manifest, _artifacts())

    assert repeated["valid"] is False
    assert repeated["committed"] is False
    assert repeated["already_committed"] is True
    violation_types = {violation["type"] for violation in repeated["violations"]}
    assert "CHAIN_BREAK" in violation_types
    conn = sqlite3.connect(db_path)
    tx_count = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE action = ?",
        (EVIDENCE_COMMIT_ACTION,),
    ).fetchone()[0]
    conn.close()
    assert tx_count == 1


def test_verify_commit_checks_global_merkle_checkpoints(tmp_path) -> None:
    db_path = str(tmp_path / "ledger.db")
    manifest = _manifest()
    commit_result = commit_evidence_manifest(db_path, manifest, _artifacts())
    assert commit_result["committed"] is True

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO merkle_roots (tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
        "VALUES ('__global__', 'bad-root', 1, 1, 1)"
    )
    conn.commit()
    conn.close()

    report = verify_evidence_commit(db_path, manifest, _artifacts())

    assert report["valid"] is False
    assert "MERKLE_MISMATCH" in {violation["type"] for violation in report["violations"]}


async def test_ledger_audit_accepts_legacy_chain_and_tenant_bound_chain(tmp_path) -> None:
    db_path = str(tmp_path / "ledger.db")
    conn = sqlite3.connect(db_path)
    ledger = SovereignLedger(conn)
    _insert_legacy_tx(conn, project="legacy-1", detail={"x": 1})
    ledger.record_transaction("tenant", "store", {"x": 2}, tenant_id="tenant-a")
    _insert_legacy_tx(conn, project="legacy-2", detail={"x": 3})
    conn.close()

    async with aiosqlite.connect(db_path) as async_conn:
        ledger = SovereignLedger(async_conn)
        full_report = await ledger.audit_integrity_async()
        tenant_report = await ledger.audit_integrity_async("tenant-a")
        default_report = await ledger.audit_integrity_async("default")

    assert full_report["valid"] is True
    assert full_report["tx_count"] == 3
    assert tenant_report["valid"] is True
    assert tenant_report["tx_count"] == 1
    assert default_report["valid"] is True
    assert default_report["tx_count"] == 2


def test_record_transaction_without_tenant_uses_default_tenant_bound_hash(tmp_path) -> None:
    db_path = str(tmp_path / "ledger.db")
    conn = sqlite3.connect(db_path)
    SovereignLedger(conn).record_transaction("default-project", "store", {"x": 1})
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT tenant_id, project, action, detail, prev_hash, hash, timestamp FROM transactions"
    ).fetchone()
    conn.close()

    assert row["tenant_id"] == "default"
    assert row["hash"] == compute_tx_hash(
        row["prev_hash"],
        row["project"],
        row["action"],
        row["detail"],
        row["timestamp"],
        tenant_id="default",
    )
    assert row["hash"] != compute_tx_hash(
        row["prev_hash"],
        row["project"],
        row["action"],
        row["detail"],
        row["timestamp"],
    )


async def test_ledger_audit_detects_tenant_transplant(tmp_path) -> None:
    db_path = str(tmp_path / "ledger.db")
    conn = sqlite3.connect(db_path)
    SovereignLedger(conn).record_transaction("tenant", "store", {"x": 1}, tenant_id="tenant-a")
    conn.execute("UPDATE transactions SET tenant_id = 'tenant-b'")
    conn.commit()
    conn.close()

    async with aiosqlite.connect(db_path) as async_conn:
        report = await SovereignLedger(async_conn).audit_integrity_async()

    assert report["valid"] is False
    assert {violation["type"] for violation in report["violations"]} == {"TAMPER_DETECTED"}
