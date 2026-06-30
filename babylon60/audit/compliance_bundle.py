# [C5-REAL] Exergy-Maximized
"""
EU AI Act Compliance Bundler (H4.2).

Exports cryptographic logs, signatures, Rekor UUIDs, and TSA tokens
into a structured `audit_bundle.zip` capable of offline verification.
"""

import json
import logging
import sqlite3
import zipfile
from pathlib import Path

logger = logging.getLogger("babylon60.audit.bundler")


class ComplianceBundler:
    """Packages the SQLite Ledger into a verifiable compliance archive."""

    def __init__(self, db_path: str = ".cortex/cortex_ledger.db") -> None:
        self.db_path = Path(db_path)

    def export_bundle(self, output_zip_path: str) -> bool:
        """
        Exports the entire ledger and associated cryptographic proofs into a ZIP file.

        Args:
            output_zip_path: Path where the ZIP archive will be saved.

        Returns:
            True if export is successful, False otherwise.
        """
        if not self.db_path.exists():
            logger.error(f"[ComplianceBundler] Database not found at {self.db_path}")
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM security_audit_log ORDER BY rowid ASC")
                rows = cursor.fetchall()

            export_data = []
            for row in rows:
                export_data.append(
                    {
                        "audit_id": row["audit_id"],
                        "timestamp": row["timestamp"],
                        "tenant_id": row["tenant_id"],
                        "actor_role": row["actor_role"],
                        "actor_id": row["actor_id"],
                        "action": row["action"],
                        "resource": row["resource"],
                        "status": row["status"],
                        "prev_hash": row["prev_hash"],
                        "signature": row["signature"],
                        "external_anchor": json.loads(row["external_anchor"])
                        if row["external_anchor"]
                        else None,
                    }
                )

            metadata = {
                "version": "1.0",
                "format": "EU_AI_ACT_COMPLIANCE",
                "total_records": len(export_data),
            }

            with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Write metadata
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))
                # Write full ledger export
                zipf.writestr("ledger_export.json", json.dumps(export_data, indent=2))

                # Write individual signatures for offline verification
                # For a huge ledger, we might chunk this, but for Phase 4 we just store it
                # to prove the structure.
                for idx, record in enumerate(export_data):
                    sig_content = {
                        "audit_id": record["audit_id"],
                        "signature": record["signature"],
                        "external_anchor": record["external_anchor"],
                    }
                    zipf.writestr(
                        f"signatures/record_{idx:06d}_{record['audit_id']}.json",
                        json.dumps(sig_content, indent=2),
                    )

            logger.info(
                f"[ComplianceBundler] Successfully exported {len(export_data)} records to {output_zip_path}"
            )
            return True

        except Exception as e:  # noqa: BLE001
            logger.error(f"[ComplianceBundler] Failed to export bundle: {e}")
            return False
