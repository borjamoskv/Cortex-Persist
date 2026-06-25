# [C5-REAL] Exergy-Maximized

import json
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
from collections.abc import Mapping
from typing import Any

from legacy_research.ledger.ledger_core import MerkleTree
from legacy_research.utils.canonical import compute_tx_hash, compute_tx_hash_v1

# Action constant used by ledger
EVIDENCE_COMMIT_ACTION = "forensic_evidence_commit"


def _commit_detail(manifest: Mapping[str, Any], normalize_fn) -> dict[str, Any]:
    bundle_id = manifest.get("bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id.strip():
        raise ValueError("bundle_id must be a non-empty string")
    tenant_id = manifest.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise ValueError("tenant_id must be a non-empty string")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("manifest artifacts must be a list")
    manifest_sha256 = manifest.get("manifest_sha256")
    if not isinstance(manifest_sha256, str) or not manifest_sha256.strip():
        raise ValueError("manifest_sha256 must be a non-empty string")

    return {
        "schema": "cortex.forensics.evidence_commit.v1",
        "bundle_id": bundle_id,
        "tenant_id": tenant_id,
        "project": manifest.get("project"),
        "profile": manifest.get("profile"),
        "manifest_sha256": manifest_sha256,
        "artifact_count": manifest.get("artifact_count"),
        "total_bytes": manifest.get("total_bytes"),
        "artifacts": [
            {
                "path": normalize_fn(entry.get("path") if isinstance(entry, Mapping) else None),
                "bytes": entry.get("bytes") if isinstance(entry, Mapping) else None,
                "sha256": entry.get("sha256") if isinstance(entry, Mapping) else None,
            }
            for entry in artifacts
        ],
    }


def _commit_project(detail: Mapping[str, Any]) -> str:
    project = detail.get("project")
    return str(project) if project else "forensics"


def _find_existing_commit(
    conn: sqlite3.Connection,
    tenant_id: str,
    bundle_id: str,
    manifest_sha256: str,
) -> sqlite3.Row | None:
    try:
        rows = conn.execute(
            "SELECT id, hash, detail FROM transactions "
            "WHERE tenant_id = ? AND action = ? ORDER BY id",
            (tenant_id, EVIDENCE_COMMIT_ACTION),
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    for row in rows:
        try:
            detail = json.loads(row["detail"] or "{}")
        except json.JSONDecodeError:
            continue
        if (
            detail.get("bundle_id") == bundle_id
            and detail.get("manifest_sha256") == manifest_sha256
        ):
            return row
    return None


def _verify_tenant_chain(conn: sqlite3.Connection, tenant_id: str) -> list[dict[str, Any]]:
    violations = []
    rows = conn.execute(
        "SELECT id, project, action, detail, prev_hash, hash, timestamp "
        "FROM transactions WHERE tenant_id = ? ORDER BY id",
        (tenant_id,),
    ).fetchall()
    expected_prev = "GENESIS"
    for row in rows:
        if row["prev_hash"] != expected_prev:
            violations.append(
                {
                    "type": "CHAIN_BREAK",
                    "tx_id": row["id"],
                    "expected": expected_prev,
                    "actual": row["prev_hash"],
                }
            )
        computed_v3 = compute_tx_hash(
            row["prev_hash"],
            row["project"],
            row["action"],
            row["detail"],
            row["timestamp"],
            tenant_id=tenant_id,
        )
        computed_v2 = compute_tx_hash(
            row["prev_hash"], row["project"], row["action"], row["detail"], row["timestamp"]
        )
        computed_v1 = compute_tx_hash_v1(
            row["prev_hash"], row["project"], row["action"], row["detail"], row["timestamp"]
        )
        if row["hash"] not in {computed_v3, computed_v2, computed_v1}:
            violations.append({"type": "TAMPER_DETECTED", "tx_id": row["id"]})
        expected_prev = row["hash"]
    return violations


def _verify_merkle_roots(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    violations = []
    try:
        roots = conn.execute(
            "SELECT COALESCE(tenant_id, '__global__') AS tenant_id, root_hash, "
            "tx_start_id, tx_end_id FROM merkle_roots ORDER BY id"
        ).fetchall()
    except sqlite3.OperationalError:
        return violations

    for root in roots:
        root_tenant_id = root["tenant_id"]
        if root_tenant_id == "__global__":
            rows = conn.execute(
                "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                (root["tx_start_id"], root["tx_end_id"]),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT hash FROM transactions "
                "WHERE tenant_id = ? AND id >= ? AND id <= ? ORDER BY id",
                (root_tenant_id, root["tx_start_id"], root["tx_end_id"]),
            ).fetchall()
        computed_root = MerkleTree([row["hash"] for row in rows]).root_hash
        if computed_root != root["root_hash"]:
            violations.append(
                {
                    "type": "MERKLE_MISMATCH",
                    "tenant_id": root_tenant_id,
                    "range": f"{root['tx_start_id']}-{root['tx_end_id']}",
                }
            )
    return violations


def _verify_existing_commit(
    conn: sqlite3.Connection,
    tenant_id: str,
    existing: sqlite3.Row,
    detail: Mapping[str, Any],
) -> list[dict[str, Any]]:
    violations = []
    try:
        stored_detail = json.loads(existing["detail"] or "{}")
    except json.JSONDecodeError:
        stored_detail = None
        violations.append({"type": "COMMIT_DETAIL_INVALID_JSON", "tx_id": existing["id"]})
    if stored_detail != detail:
        violations.append({"type": "COMMIT_DETAIL_MISMATCH", "tx_id": existing["id"]})
    violations.extend(_verify_tenant_chain(conn, tenant_id))
    violations.extend(_verify_merkle_roots(conn))
    return violations
