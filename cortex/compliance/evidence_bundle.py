"""Forensic evidence bundle export for CORTEX compliance surfaces.

The bundle is deliberately data-minimised: it exports hashes, ledger links,
verification reports, and tombstone evidence without raw fact content, raw
metadata, transaction detail payloads, or actor identifiers.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cortex.utils.canonical import canonical_json, compute_tx_hash, compute_tx_hash_v1, now_iso

__all__ = ["ForensicEvidenceBundleExporter", "write_evidence_bundle"]

_GENESIS_HASH = "GENESIS"
_ALLOWED_TABLES = frozenset(
    {"facts", "transactions", "vote_ledger", "vote_merkle_roots", "shredded_keys"}
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_optional(value: Any) -> str | None:
    if value is None:
        return None
    return _sha256_text(str(value))


def _component_hash(value: Any) -> str:
    return _sha256_text(canonical_json(value))


def _redact_identifier(value: Any) -> str | None:
    digest = _sha256_optional(value)
    return f"sha256:{digest}" if digest else None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Unsupported table name: {table_name}")
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Unsupported table name: {table_name}")
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name = ? AND type IN ('table', 'view')",
        (table_name,),
    ).fetchone()
    return row is not None


def _select_rows(
    conn: sqlite3.Connection,
    table_name: str,
    select_columns: list[str],
    *,
    tenant_id: str,
    project: str | None = None,
) -> list[sqlite3.Row]:
    columns = _table_columns(conn, table_name)
    selected = [column for column in select_columns if column in columns]
    if not selected:
        return []
    where = []
    params: list[Any] = []
    if "tenant_id" in columns:
        where.append("tenant_id = ?")
        params.append(tenant_id)
    if project is not None and "project" in columns:
        where.append("project = ?")
        params.append(project)
    sql = f"SELECT {', '.join(selected)} FROM {table_name}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    if "id" in selected:
        sql += " ORDER BY id ASC"
    return conn.execute(sql, params).fetchall()


def _build_merkle_tree(hashes: list[str]) -> str:
    if not hashes:
        return ""
    if len(hashes) == 1:
        return hashes[0]
    next_level = []
    for i in range(0, len(hashes), 2):
        left = hashes[i]
        right = hashes[i + 1] if i + 1 < len(hashes) else left
        next_level.append(_sha256_text(left + right))
    return _build_merkle_tree(next_level)


def _storage_class(content: Any) -> str:
    text = str(content or "")
    if "gdpr_crypto_shred_v1" in text:
        return "gdpr_crypto_shred_v1"
    if text.startswith("v6_aesgcm:"):
        return "v6_aesgcm"
    return "legacy_or_plaintext"


def _redact_compliance_report(report: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if report is None:
        return None
    redacted = dict(report)
    facts_summary = dict(redacted.get("facts_summary") or {})
    source_hashes: list[str] = []
    sources = facts_summary.get("sources")
    if isinstance(sources, list):
        source_hashes = [item for item in (_redact_identifier(source) for source in sources) if item]
        facts_summary["source_hashes"] = source_hashes
        facts_summary.pop("sources", None)
    redacted["facts_summary"] = facts_summary
    eu_ai_act = dict(redacted.get("eu_ai_act") or {})
    checks = dict(eu_ai_act.get("checks") or {})
    traceability = checks.get("art_12_2d_agent_traceability")
    if isinstance(traceability, dict):
        check = dict(traceability)
        check["evidence"] = f"{len(source_hashes)} distinct source hashes"
        checks["art_12_2d_agent_traceability"] = check
    eu_ai_act["checks"] = checks
    redacted["eu_ai_act"] = eu_ai_act
    redacted.pop("facts", None)
    return redacted


def _write_atomic(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(data, encoding="utf-8")
    os.replace(tmp_path, path)


def write_evidence_bundle(
    bundle: Mapping[str, Any],
    output_path: str | Path,
) -> dict[str, str]:
    """Write a canonical evidence bundle plus SHA-256 sidecar atomically."""
    path = Path(output_path)
    payload = canonical_json(bundle) + "\n"
    digest = _sha256_text(payload)
    _write_atomic(path, payload)
    sidecar = path.with_suffix(path.suffix + ".sha256.json")
    sidecar_payload = canonical_json(
        {
            "schema": "cortex.forensic_evidence_bundle.sha256.v1",
            "artifact": str(path),
            "sha256": digest,
            "bytes": len(payload.encode("utf-8")),
            "bundle_hash": str(bundle.get("bundle_hash", "")),
        }
    )
    _write_atomic(sidecar, sidecar_payload + "\n")
    return {"artifact": str(path), "sha256_sidecar": str(sidecar), "sha256": digest}


class ForensicEvidenceBundleExporter:
    """Build data-minimised forensic evidence bundles from a CORTEX SQLite DB."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def build(
        self,
        *,
        project: str | None = None,
        tenant_id: str = "default",
        compliance_report: Mapping[str, Any] | None = None,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        """Return a canonical, hash-addressed evidence bundle."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            fact_manifest = self._collect_facts(conn, tenant_id=tenant_id, project=project)
            transaction_manifest = self._collect_transactions(
                conn, tenant_id=tenant_id, project=None
            )
            vote_manifest = self._collect_vote_ledger(conn, tenant_id=tenant_id)
            vote_merkle_roots = self._collect_vote_merkle_roots(conn, tenant_id=tenant_id)
            shredding_manifest = self._collect_shredding(conn, tenant_id=tenant_id)
            fact_hashes_by_id = self._fact_hashes_by_id(
                self._collect_facts(conn, tenant_id=tenant_id, project=None)
            )
            reports = {
                "compliance": _redact_compliance_report(compliance_report),
                "transactions": self._verify_transactions(transaction_manifest),
                "vote_ledger": self._verify_vote_ledger(
                    vote_manifest,
                    vote_merkle_roots,
                    fact_hashes_by_id,
                ),
            }
        finally:
            conn.close()

        components = {
            "facts": fact_manifest,
            "transactions": transaction_manifest,
            "vote_ledger": vote_manifest,
            "vote_merkle_roots": vote_merkle_roots,
            "shredding": shredding_manifest,
            "reports": reports,
        }
        component_hashes = {
            name: _component_hash(value) for name, value in sorted(components.items())
        }
        payload = {
            "schema": "cortex.forensic_evidence_bundle.payload.v1",
            "generated_at": generated_at or now_iso(),
            "tenant_id": tenant_id,
            "project": project,
            "component_hashes": component_hashes,
            **components,
        }
        return {
            "schema": "cortex.forensic_evidence_bundle.v1",
            "bundle_hash": _component_hash(payload),
            "payload": payload,
        }

    def write(
        self,
        output_path: str | Path,
        *,
        project: str | None = None,
        tenant_id: str = "default",
        compliance_report: Mapping[str, Any] | None = None,
        generated_at: str | None = None,
    ) -> dict[str, str]:
        """Build and write the bundle plus SHA-256 sidecar."""
        bundle = self.build(
            project=project,
            tenant_id=tenant_id,
            compliance_report=compliance_report,
            generated_at=generated_at,
        )
        return write_evidence_bundle(bundle, output_path)

    def _collect_facts(
        self,
        conn: sqlite3.Connection,
        *,
        tenant_id: str,
        project: str | None,
    ) -> list[dict[str, Any]]:
        if not _table_exists(conn, "facts"):
            return []
        rows = _select_rows(
            conn,
            "facts",
            [
                "id",
                "tenant_id",
                "project",
                "content",
                "metadata",
                "hash",
                "tx_id",
                "valid_until",
                "is_tombstoned",
                "source",
                "signature",
                "signer_pubkey",
                "created_at",
                "updated_at",
            ],
            tenant_id=tenant_id,
            project=project,
        )
        facts = []
        for row in rows:
            item = dict(row)
            facts.append(
                {
                    "id": item.get("id"),
                    "tenant_id": item.get("tenant_id"),
                    "project": item.get("project"),
                    "hash": item.get("hash"),
                    "tx_id": item.get("tx_id"),
                    "valid_until": item.get("valid_until"),
                    "is_tombstoned": bool(item.get("is_tombstoned", 0)),
                    "storage_class": _storage_class(item.get("content")),
                    "stored_content_sha256": _sha256_optional(item.get("content")),
                    "metadata_storage_sha256": _sha256_optional(item.get("metadata")),
                    "source_sha256": _redact_identifier(item.get("source")),
                    "signature_sha256": _sha256_optional(item.get("signature")),
                    "signer_pubkey_sha256": _sha256_optional(item.get("signer_pubkey")),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                }
            )
        return facts

    def _collect_transactions(
        self,
        conn: sqlite3.Connection,
        *,
        tenant_id: str,
        project: str | None,
    ) -> list[dict[str, Any]]:
        if not _table_exists(conn, "transactions"):
            return []
        rows = _select_rows(
            conn,
            "transactions",
            ["id", "tenant_id", "project", "action", "detail", "prev_hash", "hash", "timestamp"],
            tenant_id=tenant_id,
            project=project,
        )
        transactions = []
        for row in rows:
            item = dict(row)
            detail = item.get("detail")
            transactions.append(
                {
                    "id": item.get("id"),
                    "tenant_id": item.get("tenant_id"),
                    "project": item.get("project"),
                    "action": item.get("action"),
                    "detail_sha256": _sha256_optional(detail),
                    "detail_bytes": len(str(detail or "").encode("utf-8")),
                    "prev_hash": item.get("prev_hash"),
                    "hash": item.get("hash"),
                    "timestamp": item.get("timestamp"),
                    "_detail": detail,
                }
            )
        return transactions

    def _collect_vote_ledger(
        self,
        conn: sqlite3.Connection,
        *,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        if not _table_exists(conn, "vote_ledger"):
            return []
        rows = _select_rows(
            conn,
            "vote_ledger",
            [
                "id",
                "tenant_id",
                "fact_id",
                "fact_hash",
                "agent_id",
                "vote",
                "vote_weight",
                "prev_hash",
                "hash",
                "timestamp",
                "signature",
            ],
            tenant_id=tenant_id,
        )
        votes = []
        for row in rows:
            item = dict(row)
            votes.append(
                {
                    "id": item.get("id"),
                    "tenant_id": item.get("tenant_id"),
                    "fact_id": item.get("fact_id"),
                    "fact_hash": item.get("fact_hash"),
                    "agent_id_sha256": _redact_identifier(item.get("agent_id")),
                    "vote": item.get("vote"),
                    "vote_weight": item.get("vote_weight"),
                    "prev_hash": item.get("prev_hash"),
                    "hash": item.get("hash"),
                    "timestamp": item.get("timestamp"),
                    "signature_sha256": _sha256_optional(item.get("signature")),
                    "_agent_id": item.get("agent_id"),
                    "_signature": item.get("signature"),
                }
            )
        return votes

    def _collect_vote_merkle_roots(
        self,
        conn: sqlite3.Connection,
        *,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        if not _table_exists(conn, "vote_merkle_roots"):
            return []
        rows = _select_rows(
            conn,
            "vote_merkle_roots",
            ["id", "tenant_id", "root_hash", "vote_start_id", "vote_end_id", "vote_count", "created_at"],
            tenant_id=tenant_id,
        )
        return [dict(row) for row in rows]

    def _collect_shredding(
        self,
        conn: sqlite3.Connection,
        *,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        if not _table_exists(conn, "shredded_keys"):
            return []
        rows = _select_rows(
            conn,
            "shredded_keys",
            ["id", "fact_id", "tenant_id", "reason", "shredded_by", "shredded_at"],
            tenant_id=tenant_id,
        )
        return [
            {
                "id": row["id"],
                "fact_id": row["fact_id"],
                "tenant_id": row["tenant_id"],
                "reason": row["reason"],
                "shredded_by_sha256": _redact_identifier(row["shredded_by"]),
                "shredded_at": row["shredded_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _fact_hashes_by_id(facts: list[dict[str, Any]]) -> dict[int, str]:
        return {
            int(fact["id"]): str(fact["hash"])
            for fact in facts
            if fact.get("id") is not None and fact.get("hash")
        }

    def _verify_transactions(self, transactions: list[dict[str, Any]]) -> dict[str, Any]:
        violations = []
        current_prev_hash = _GENESIS_HASH
        for tx in transactions:
            prev_hash = str(tx.get("prev_hash") or _GENESIS_HASH)
            if prev_hash != current_prev_hash:
                violations.append(
                    {
                        "type": "chain_break",
                        "tx_id": tx.get("id"),
                        "expected_prev_hash": current_prev_hash,
                        "actual_prev_hash": prev_hash,
                    }
                )
            detail = str(tx.pop("_detail", "") or "")
            stored_hash = str(tx.get("hash") or "")
            timestamp = str(tx.get("timestamp") or "")
            project = str(tx.get("project") or "")
            action = str(tx.get("action") or "")
            tenant_id = str(tx.get("tenant_id") or "")
            acceptable_hashes = {
                compute_tx_hash(prev_hash, project, action, detail, timestamp, tenant_id=tenant_id),
                compute_tx_hash(prev_hash, project, action, detail, timestamp),
                compute_tx_hash_v1(prev_hash, project, action, detail, timestamp),
            }
            if stored_hash not in acceptable_hashes:
                violations.append({"type": "hash_mismatch", "tx_id": tx.get("id")})
            current_prev_hash = stored_hash

        return {
            "valid": len(violations) == 0,
            "tx_checked": len(transactions),
            "violations": violations,
        }

    def _verify_vote_ledger(
        self,
        votes: list[dict[str, Any]],
        merkle_roots: list[dict[str, Any]],
        facts_by_id: dict[int, str],
    ) -> dict[str, Any]:
        violations = []
        current_prev_hash = _GENESIS_HASH
        for vote in votes:
            prev_hash = str(vote.get("prev_hash") or _GENESIS_HASH)
            if prev_hash != current_prev_hash:
                violations.append(
                    {
                        "type": "chain_break",
                        "vote_id": vote.get("id"),
                        "expected_prev_hash": current_prev_hash,
                        "actual_prev_hash": prev_hash,
                    }
                )
            fact_id = int(vote["fact_id"])
            fact_hash = str(vote.get("fact_hash") or "")
            if not fact_hash:
                violations.append({"type": "unbound_fact_hash", "vote_id": vote.get("id")})
            elif facts_by_id.get(fact_id) != fact_hash:
                violations.append(
                    {
                        "type": "fact_hash_mismatch",
                        "vote_id": vote.get("id"),
                        "fact_id": fact_id,
                        "expected_fact_hash": fact_hash,
                        "actual_fact_hash": facts_by_id.get(fact_id),
                    }
                )
            expected_hash = _sha256_text(
                canonical_json(
                    {
                        "schema": "vote_ledger_v2",
                        "tenant_id": vote.get("tenant_id"),
                        "prev_hash": prev_hash,
                        "fact_id": fact_id,
                        "fact_hash": fact_hash,
                        "agent_id": vote.pop("_agent_id") or "",
                        "vote": str(vote.get("vote")),
                        "vote_weight": vote.get("vote_weight"),
                        "timestamp": vote.get("timestamp"),
                        "signature": vote.pop("_signature") or "",
                    }
                )
            )
            if expected_hash != vote.get("hash"):
                violations.append({"type": "hash_mismatch", "vote_id": vote.get("id")})
            current_prev_hash = str(vote.get("hash") or "")

        for root in merkle_roots:
            start = int(root["vote_start_id"])
            end = int(root["vote_end_id"])
            scoped_hashes = [
                str(vote["hash"]) for vote in votes if start <= int(vote["id"]) <= end
            ]
            actual = _build_merkle_tree(scoped_hashes)
            if actual != root["root_hash"] or len(scoped_hashes) != int(root["vote_count"]):
                violations.append(
                    {
                        "type": "vote_merkle_mismatch",
                        "checkpoint_id": root["id"],
                        "expected": root["root_hash"],
                        "actual": actual,
                    }
                )

        return {
            "valid": len(violations) == 0,
            "votes_checked": len(votes),
            "checkpoints_checked": len(merkle_roots),
            "violations": violations,
        }
