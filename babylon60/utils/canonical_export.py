# [C5-REAL] Exergy-Maximized
"""
Canonical Export Format for CORTEX/BABYLON-60.

Implements the 20-Year Survivability Principle 1:
"The data format IS the product. Programs are ephemeral. Data is permanent."

Exports facts, ledger entries, and metadata in a self-describing JSONL format
that can be parsed with Python stdlib (json), jq, or any future language
without installing CORTEX or any dependency.

Schema version: 1.0.0
Author: Borja Moskv (SYS_ID: borjamoskv)
"""

from __future__ import annotations

from babylon60.crypto.hash_registry import cortex_hash
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

__all__ = [
    "CanonicalExporter",
    "CANONICAL_SCHEMA_VERSION",
]

if TYPE_CHECKING:
    from babylon60.engine.cognitive.models import Fact

CANONICAL_SCHEMA_VERSION = "1.0.0"

# Self-describing header that is emitted as the first line of every canonical export.
# Any consumer can parse this line to understand the schema without external docs.
CANONICAL_SCHEMA_HEADER = {
    "_cortex_canonical": True,
    "_schema_version": CANONICAL_SCHEMA_VERSION,
    "_schema_url": "https://github.com/borjamoskv/cortex-persist/blob/main/docs/canonical-export-schema.md",
    "_record_types": ["fact", "ledger_entry", "metadata"],
    "_field_definitions": {
        "fact": {
            "id": "integer | string — Unique fact identifier",
            "tenant_id": "string — Tenant namespace",
            "project": "string — Project namespace",
            "content": "string — The fact content (UTF-8)",
            "fact_type": "string — Semantic type (rule, insight, axiom, observation, etc.)",
            "tags": "list[string] — Classification tags",
            "confidence": "string — Epistemic confidence level (C1-C5)",
            "source": "string | null — Origin of the fact",
            "hash": "string | null — SHA-256 content hash",
            "created_at": "string | null — ISO 8601 timestamp",
            "valid_from": "string | null — Temporal validity start",
            "valid_until": "string | null — Temporal validity end (null = still valid)",
            "is_tombstoned": "boolean — Logical deletion flag",
            "is_quarantined": "boolean — Guard rejection flag",
            "exergy_score": "float — Thermodynamic utility score [0.0, 1.0]",
            "consensus_score": "float — BFT consensus agreement [0.0, 1.0]",
        },
        "ledger_entry": {
            "sequence": "integer — Monotonic sequence number",
            "action": "string — Action type (store, update, delete, verify)",
            "fact_id": "integer | null — Related fact ID",
            "agent_id": "string — Agent that performed the action",
            "timestamp": "string — ISO 8601 timestamp",
            "prev_hash": "string — SHA-256 hash of previous entry",
            "entry_hash": "string — SHA-256 hash of this entry",
        },
        "metadata": {
            "export_timestamp": "string — ISO 8601 export time",
            "exporter_version": "string — CORTEX version that generated the export",
            "total_facts": "integer — Total fact count",
            "total_ledger_entries": "integer — Total ledger entry count",
            "db_path": "string — Source database path",
            "integrity_hash": "string — SHA-256 of the entire export payload",
        },
    },
}


@dataclass(frozen=True)
class CanonicalRecord:
    """A single record in the canonical export format."""

    record_type: str  # "fact", "ledger_entry", "metadata", "_schema"
    data: dict[str, Any]
    sequence: int

    def to_jsonl_line(self) -> str:
        """Serialize to a single JSON line with envelope metadata."""
        envelope = {
            "_type": self.record_type,
            "_seq": self.sequence,
            "_ts": datetime.now(tz=timezone.utc).isoformat(),
            **self.data,
        }
        return json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))


class CanonicalExporter:
    """Exports CORTEX data in the self-describing canonical JSONL format.

    The export is designed to be readable in 20+ years with zero dependencies:
    - Line 1: Schema header (self-describing field definitions)
    - Lines 2..N: Fact records
    - Lines N+1..M: Ledger entries (if included)
    - Last line: Metadata record with integrity hash
    """

    def __init__(self) -> None:
        self._records: list[CanonicalRecord] = []
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def add_fact(self, fact: Fact) -> None:
        """Add a fact to the export buffer."""
        d = fact.to_dict()
        # Ensure consistent field naming for canonical format
        canonical_data = {
            "id": d.get("id"),
            "tenant_id": d.get("tenant_id", "default"),
            "project": d.get("project", ""),
            "content": d.get("content", ""),
            "fact_type": d.get("fact_type", d.get("type", "")),
            "tags": d.get("tags", []),
            "confidence": d.get("confidence", "C3"),
            "source": d.get("source"),
            "hash": d.get("hash"),
            "created_at": d.get("created_at"),
            "updated_at": d.get("updated_at"),
            "valid_from": d.get("valid_from"),
            "valid_until": d.get("valid_until"),
            "is_tombstoned": d.get("is_tombstoned", False),
            "is_quarantined": d.get("is_quarantined", False),
            "exergy_score": d.get("exergy_score", 1.0),
            "consensus_score": d.get("consensus_score", 1.0),
            "category": d.get("category", "general"),
            "quadrant": d.get("quadrant", "ACTIVE"),
            "parent_id": d.get("parent_id"),
            "meta": d.get("meta", {}),
        }
        self._records.append(
            CanonicalRecord(
                record_type="fact",
                data=canonical_data,
                sequence=self._next_seq(),
            )
        )

    def add_ledger_entry(self, entry: dict[str, Any]) -> None:
        """Add a ledger hash-chain entry to the export buffer."""
        canonical_data = {
            "sequence": entry.get("sequence", entry.get("id")),
            "action": entry.get("action", entry.get("event_type", "")),
            "fact_id": entry.get("fact_id"),
            "agent_id": entry.get("agent_id", "unknown"),
            "timestamp": entry.get("timestamp", entry.get("created_at", "")),
            "prev_hash": entry.get("prev_hash", ""),
            "entry_hash": entry.get("entry_hash", entry.get("hash", "")),
            "payload": entry.get("payload", {}),
        }
        self._records.append(
            CanonicalRecord(
                record_type="ledger_entry",
                data=canonical_data,
                sequence=self._next_seq(),
            )
        )

    def export(self, db_path: str = "", cortex_version: str = "1.0.0") -> str:
        """Generate the complete canonical JSONL export.

        Returns:
            A string containing the full JSONL export with schema header,
            records, and integrity metadata footer.
        """
        lines: list[str] = []

        # Line 1: Self-describing schema header
        schema_record = CanonicalRecord(
            record_type="_schema",
            data=CANONICAL_SCHEMA_HEADER,
            sequence=0,
        )
        lines.append(schema_record.to_jsonl_line())

        # Lines 2..N: All records (facts + ledger entries)
        for record in self._records:
            lines.append(record.to_jsonl_line())

        # Count by type
        fact_count = sum(1 for r in self._records if r.record_type == "fact")
        ledger_count = sum(1 for r in self._records if r.record_type == "ledger_entry")

        # Compute integrity hash over all record lines (excluding schema and metadata)
        payload_text = "\n".join(lines[1:])
        integrity_hash = cortex_hash(payload_text.encode("utf-8"))

        # Last line: Metadata footer
        metadata = CanonicalRecord(
            record_type="metadata",
            data={
                "export_timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "exporter_version": cortex_version,
                "schema_version": CANONICAL_SCHEMA_VERSION,
                "total_facts": fact_count,
                "total_ledger_entries": ledger_count,
                "total_records": len(self._records),
                "db_path": db_path,
                "integrity_hash": integrity_hash,
                "author": "borjamoskv",
            },
            sequence=self._next_seq(),
        )
        lines.append(metadata.to_jsonl_line())

        return "\n".join(lines) + "\n"

    def export_to_file(self, filepath: str, db_path: str = "", cortex_version: str = "1.0.0") -> str:
        """Export and write to a file. Returns the integrity hash."""
        content = self.export(db_path=db_path, cortex_version=cortex_version)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Extract integrity hash from last line
        last_line = content.strip().split("\n")[-1]
        meta = json.loads(last_line)
        return meta.get("integrity_hash", "")
