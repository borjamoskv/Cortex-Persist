# [C5-REAL] Exergy-Maximized
"""Canonical forensic evidence manifests and ledger commitments.

The manifest functions verify local artifact bytes. The commitment functions
append a raw-free digest record to the canonical transaction ledger only after
manifest verification succeeds.
"""

from __future__ import annotations

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
from pathlib import PurePosixPath
from typing import Any

from legacy_research.database.core import connect
from legacy_research.forensics._evidence_ledger import (
    EVIDENCE_COMMIT_ACTION,
    _commit_detail,
    _commit_project,
    _find_existing_commit,
    _verify_existing_commit,
)
from legacy_research.forensics.crypto.hashing import (
    canonical_json_bytes,
    sha256_hex,
)
from legacy_research.forensics.crypto.hashing import (
    manifest_sha256 as _manifest_sha256,
)
from legacy_research.ledger.ledger_core import SovereignLedger
from legacy_research.utils.canonical import now_iso

EVIDENCE_MANIFEST_SCHEMA = "cortex.forensics.evidence_manifest.v1"

__all__ = [
    "EVIDENCE_COMMIT_ACTION",
    "EVIDENCE_MANIFEST_SCHEMA",
    "build_evidence_manifest",
    "canonical_json_bytes",
    "commit_evidence_manifest",
    "dump_evidence_manifest",
    "load_evidence_manifest_bytes",
    "sha256_hex",
    "verify_evidence_commit",
    "verify_evidence_manifest",
]


def build_evidence_manifest(
    artifacts: Mapping[str, bytes | bytearray | memoryview],
    *,
    bundle_id: str,
    tenant_id: str,
    project: str | None = None,
    generated_at: str | None = None,
    profile: str = "customer-confidential",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic manifest for a set of evidence artifacts."""
    if not artifacts:
        raise ValueError("evidence manifest requires at least one artifact")

    entries: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    total_bytes = 0
    for raw_path, raw_bytes in artifacts.items():
        path = _normalize_artifact_path(raw_path)
        if path in seen_paths:
            raise ValueError(f"duplicate evidence artifact path: {path}")
        seen_paths.add(path)
        artifact_bytes = _coerce_bytes(raw_bytes, path)
        total_bytes += len(artifact_bytes)
        entries.append(
            {
                "path": path,
                "bytes": len(artifact_bytes),
                "sha256": sha256_hex(artifact_bytes),
            }
        )

    manifest: dict[str, Any] = {
        "schema": EVIDENCE_MANIFEST_SCHEMA,
        "bundle_id": _require_nonempty(bundle_id, "bundle_id"),
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "project": project,
        "generated_at": generated_at or now_iso(),
        "profile": _require_nonempty(profile, "profile"),
        "algorithms": {
            "artifact_hash": "sha256(raw artifact bytes)",
            "manifest_hash": "sha256(canonical_json(manifest without manifest_sha256))",
            "ledger_hash": "sha256(v3 tenant-bound; v2/v1 legacy verification accepted)",
            "canonical_json": "json.dumps(sort_keys=True,separators=(',',':'),ensure_ascii=True)",
        },
        "artifact_count": len(entries),
        "total_bytes": total_bytes,
        "artifacts": sorted(entries, key=lambda entry: str(entry["path"])),
    }
    if metadata is not None:
        manifest["metadata"] = dict(metadata)
    manifest["manifest_sha256"] = _manifest_sha256(manifest)
    return manifest


def verify_evidence_manifest(
    manifest: Mapping[str, Any],
    artifacts: Mapping[str, bytes | bytearray | memoryview],
) -> dict[str, Any]:
    """Verify a manifest against supplied artifact bytes without source access."""
    violations: list[dict[str, Any]] = []
    if manifest.get("schema") != EVIDENCE_MANIFEST_SCHEMA:
        violations.append(
            {
                "type": "MANIFEST_SCHEMA_UNSUPPORTED",
                "schema": manifest.get("schema"),
            }
        )

    expected_manifest_hash = manifest.get("manifest_sha256")
    actual_manifest_hash = _manifest_sha256(manifest)
    if expected_manifest_hash != actual_manifest_hash:
        violations.append(
            {
                "type": "MANIFEST_HASH_MISMATCH",
                "expected": expected_manifest_hash,
                "actual": actual_manifest_hash,
            }
        )

    manifest_entries = manifest.get("artifacts")
    if not isinstance(manifest_entries, list):
        return {
            "valid": False,
            "violations": violations + [{"type": "MANIFEST_ARTIFACTS_INVALID"}],
            "checked": {"artifacts": 0, "bytes": 0},
        }

    expected_by_path: dict[str, Mapping[str, Any]] = {}
    checked_bytes = 0
    for entry in manifest_entries:
        if not isinstance(entry, Mapping):
            violations.append({"type": "MANIFEST_ARTIFACT_INVALID", "path": None})
            continue
        raw_path = entry.get("path")
        try:
            path = _normalize_artifact_path(raw_path)
        except ValueError as exc:
            violations.append(
                {
                    "type": "MANIFEST_ARTIFACT_PATH_INVALID",
                    "path": raw_path,
                    "error": str(exc),
                }
            )
            continue
        if path in expected_by_path:
            violations.append({"type": "MANIFEST_ARTIFACT_DUPLICATE", "path": path})
            continue
        expected_by_path[path] = entry

    actual_by_path: dict[str, bytes] = {}
    for raw_path, raw_bytes in artifacts.items():
        try:
            path = _normalize_artifact_path(raw_path)
            actual_by_path[path] = _coerce_bytes(raw_bytes, path)
        except ValueError as exc:
            violations.append(
                {
                    "type": "ARTIFACT_INPUT_INVALID",
                    "path": raw_path,
                    "error": str(exc),
                }
            )

    for path in sorted(expected_by_path):
        entry = expected_by_path[path]
        artifact_bytes = actual_by_path.get(path)
        if artifact_bytes is None:
            violations.append({"type": "ARTIFACT_MISSING", "path": path})
            continue
        checked_bytes += len(artifact_bytes)

        expected_bytes = entry.get("bytes")
        if expected_bytes != len(artifact_bytes):
            violations.append(
                {
                    "type": "ARTIFACT_BYTES_MISMATCH",
                    "path": path,
                    "expected": expected_bytes,
                    "actual": len(artifact_bytes),
                }
            )

        expected_sha256 = entry.get("sha256")
        actual_sha256 = sha256_hex(artifact_bytes)
        if expected_sha256 != actual_sha256:
            violations.append(
                {
                    "type": "ARTIFACT_HASH_MISMATCH",
                    "path": path,
                    "expected": expected_sha256,
                    "actual": actual_sha256,
                }
            )

    for path in sorted(set(actual_by_path) - set(expected_by_path)):
        violations.append({"type": "ARTIFACT_UNEXPECTED", "path": path})

    expected_count = manifest.get("artifact_count")
    if expected_count != len(expected_by_path):
        violations.append(
            {
                "type": "MANIFEST_ARTIFACT_COUNT_MISMATCH",
                "expected": expected_count,
                "actual": len(expected_by_path),
            }
        )

    expected_total = manifest.get("total_bytes")
    if expected_total != checked_bytes:
        violations.append(
            {
                "type": "MANIFEST_TOTAL_BYTES_MISMATCH",
                "expected": expected_total,
                "actual": checked_bytes,
            }
        )

    return {
        "valid": not violations,
        "violations": violations,
        "checked": {
            "artifacts": len(expected_by_path),
            "bytes": checked_bytes,
            "input_artifacts": len(actual_by_path),
            "input_bytes": sum(len(data) for data in actual_by_path.values()),
        },
    }


def commit_evidence_manifest(
    db_path: str,
    manifest: Mapping[str, Any],
    artifacts: Mapping[str, bytes | bytearray | memoryview],
) -> dict[str, Any]:
    """Verify a manifest and commit its digest metadata to the transaction ledger."""
    verification = verify_evidence_manifest(manifest, artifacts)
    if verification["valid"] is not True:
        return {
            "valid": False,
            "committed": False,
            "already_committed": False,
            "verification": verification,
        }

    try:
        detail = _commit_detail(manifest, _normalize_artifact_path)
    except ValueError as exc:
        return {
            "valid": False,
            "committed": False,
            "already_committed": False,
            "violations": [{"type": "COMMIT_DETAIL_INVALID", "error": str(exc)}],
            "tx_id": None,
            "tx_hash": None,
            "tenant_id": None,
            "manifest_sha256": manifest.get("manifest_sha256"),
            "verification": verification,
        }
    tenant_id = detail["tenant_id"]
    conn = connect(db_path, row_factory=sqlite3.Row)
    try:
        ledger = SovereignLedger(conn)
        conn.execute("BEGIN EXCLUSIVE")
        existing = _find_existing_commit(
            conn,
            tenant_id,
            detail["bundle_id"],
            detail["manifest_sha256"],
        )
        if existing is not None:
            violations = _verify_existing_commit(conn, tenant_id, existing, detail)
            if violations:
                conn.rollback()
                return {
                    "valid": False,
                    "committed": False,
                    "already_committed": True,
                    "violations": violations,
                    "tx_id": existing["id"],
                    "tx_hash": existing["hash"],
                    "tenant_id": tenant_id,
                    "manifest_sha256": detail["manifest_sha256"],
                    "verification": verification,
                }
            conn.commit()
            return {
                "valid": True,
                "committed": True,
                "already_committed": True,
                "tx_id": existing["id"],
                "tx_hash": existing["hash"],
                "tenant_id": tenant_id,
                "manifest_sha256": detail["manifest_sha256"],
                "verification": verification,
            }

        tx_hash = ledger.record_transaction_in_current_transaction(
            _commit_project(detail),
            EVIDENCE_COMMIT_ACTION,
            detail,
            tenant_id=tenant_id,
        )
        row = conn.execute(
            "SELECT id, hash FROM transactions WHERE tenant_id = ? AND hash = ?",
            (tenant_id, tx_hash),
        ).fetchone()
        result = {
            "valid": True,
            "committed": True,
            "already_committed": False,
            "tx_id": row["id"] if row else None,
            "tx_hash": tx_hash,
            "tenant_id": tenant_id,
            "manifest_sha256": detail["manifest_sha256"],
            "verification": verification,
        }
        conn.commit()
        return result
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_evidence_commit(
    db_path: str,
    manifest: Mapping[str, Any],
    artifacts: Mapping[str, bytes | bytearray | memoryview],
) -> dict[str, Any]:
    """Verify local evidence and its matching ledger commitment."""
    verification = verify_evidence_manifest(manifest, artifacts)
    violations: list[dict[str, Any]] = []
    if verification["valid"] is not True:
        violations.append({"type": "MANIFEST_INVALID", "violations": verification["violations"]})

    try:
        detail = _commit_detail(manifest, _normalize_artifact_path)
    except ValueError as exc:
        violations.append({"type": "COMMIT_DETAIL_INVALID", "error": str(exc)})
        return {
            "valid": False,
            "violations": violations,
            "tx_id": None,
            "tx_hash": None,
            "tenant_id": None,
            "manifest_sha256": manifest.get("manifest_sha256"),
            "verification": verification,
        }
    tenant_id = detail["tenant_id"]
    conn = connect(db_path, row_factory=sqlite3.Row)
    try:
        existing = _find_existing_commit(
            conn, tenant_id, detail["bundle_id"], detail["manifest_sha256"]
        )
        if existing is None:
            violations.append(
                {
                    "type": "COMMIT_MISSING",
                    "tenant_id": tenant_id,
                    "bundle_id": detail["bundle_id"],
                    "manifest_sha256": detail["manifest_sha256"],
                }
            )
            tx_id = None
            tx_hash = None
        else:
            tx_id = existing["id"]
            tx_hash = existing["hash"]
            violations.extend(_verify_existing_commit(conn, tenant_id, existing, detail))

        return {
            "valid": not violations,
            "violations": violations,
            "tx_id": tx_id,
            "tx_hash": tx_hash,
            "tenant_id": tenant_id,
            "manifest_sha256": detail["manifest_sha256"],
            "verification": verification,
        }
    finally:
        conn.close()


def dump_evidence_manifest(manifest: Mapping[str, Any]) -> bytes:
    """Serialize a manifest as canonical JSON bytes."""
    return canonical_json_bytes(manifest)


def load_evidence_manifest_bytes(data: bytes | str) -> dict[str, Any]:
    """Parse a manifest from bytes or text and reject non-object JSON."""
    raw = data.decode("utf-8") if isinstance(data, bytes) else data
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid evidence manifest JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("invalid evidence manifest schema")
    return parsed


def _normalize_artifact_path(raw_path: object) -> str:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("artifact path must be a non-empty relative POSIX path")
    if "\\" in raw_path:
        raise ValueError("artifact path must use POSIX '/' separators")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or path.name == "" or str(path) in {"", "."}:
        raise ValueError("artifact path must be relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("artifact path must not contain traversal or empty segments")
    canonical_path = str(path)
    if canonical_path != raw_path:
        raise ValueError("artifact path must already be canonical")
    return canonical_path


def _coerce_bytes(data: bytes | bytearray | memoryview, path: str) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    raise ValueError(f"artifact {path} must be bytes")


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value
