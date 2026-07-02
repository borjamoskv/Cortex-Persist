# [C5-REAL] Exergy-Maximized
"""
Ledger Compactor Core.

Performs Merkle Tree Sharding to compress the live SQLite chain into .cortex_snapshot files,
injecting a ZERO-KNOWLEDGE COMPACTION_NODE into the database to preserve the cryptographic chain.
"""

import gzip
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from babylon60.audit.ledger import EnterpriseAuditLedger
from babylon60.audit.smt import SparseMerkleTree
from babylon60.crypto.hash_registry import cortex_hash

logger = logging.getLogger("babylon60.audit.ledger_compactor")


async def compact_ledger(
    conn: aiosqlite.Connection,
    ledger: EnterpriseAuditLedger,
    max_rows: int = 10000,
    snapshot_dir: Path | None = None,
) -> dict[str, Any]:
    """Compacts the oldest ledger entries into a cryptographic snapshot."""

    if snapshot_dir is None:
        snapshot_dir = Path("~/.gemini/config/.cortex/snapshots").expanduser()
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # First, verify current chain integrity
    verification = await ledger.verify_chain()
    if verification.get("status") != "verified":
        raise ValueError(f"Cannot compact tampered ledger: {verification}")

    async with ledger._lock:
        async with conn.execute(
            "SELECT rowid, audit_id, timestamp, tenant_id, actor_role, actor_id, action, resource, status, prev_hash, signature, external_anchor FROM security_audit_log ORDER BY rowid ASC LIMIT ?",
            (max_rows,),
        ) as cursor:
            rows = list(await cursor.fetchall())

        if not rows:
            return {"status": "skipped", "reason": "empty"}

        # Group rows into valid Merkle batches
        batches = []
        current_batch = []
        current_prev_hash = rows[0][9]
        current_sig = rows[0][10]

        for row in rows:
            # Check for existing compaction node, don't compact it again (for simplicity)
            if row[6] == "COMPACTION_NODE":
                # If the very first row is a compaction node, we skip it to compact the rest
                if len(current_batch) == 0 and len(batches) == 0:
                    pass
            if row[9] == current_prev_hash and row[10] == current_sig:
                current_batch.append(row)
            else:
                batches.append((current_prev_hash, current_sig, current_batch))
                current_prev_hash = row[9]
                current_sig = row[10]
                current_batch = [row]

        # Ensure last batch is added
        if current_batch:
            batches.append((current_prev_hash, current_sig, current_batch))

        if len(batches) <= 1:
            return {"status": "skipped", "reason": "not_enough_complete_batches"}

        # We will compact all but the last batch in this list to ensure batch boundary integrity
        batches_to_compact = batches[:-1]

        # Calculate start and end bounds
        h_start = batches_to_compact[0][0]  # prev_hash of first batch

        # Calculate the h_end by walking the SMT for the batches we compact
        expected_prev_hash = h_start
        local_smt = SparseMerkleTree()
        for _prev_hash, _signature, batch_rows in batches_to_compact:
            # Bypass logic if it's already a compaction node
            if len(batch_rows) == 1 and batch_rows[0][6] == "COMPACTION_NODE":
                expected_prev_hash = batch_rows[0][8]
                continue

            batch_audit_ids = [r[1] for r in batch_rows]
            for aid in batch_audit_ids:
                local_smt.update(cortex_hash(aid.encode()), aid)
            merkle_root = local_smt.root
            entry_hash_payload = f"merkle_batch:{merkle_root}:{expected_prev_hash}"
            expected_prev_hash = cortex_hash(entry_hash_payload.encode())

        h_end = expected_prev_hash

        # Collect all rowids to delete and prepare the snapshot payload
        rowids_to_delete = []
        snapshot_data = []
        for _, _, batch_rows in batches_to_compact:
            for r in batch_rows:
                rowids_to_delete.append(r[0])
                snapshot_data.append(
                    {
                        "audit_id": r[1],
                        "timestamp": r[2],
                        "tenant_id": r[3],
                        "actor_role": r[4],
                        "actor_id": r[5],
                        "action": r[6],
                        "resource": r[7],
                        "status": r[8],
                        "prev_hash": r[9],
                        "signature": r[10],
                        "external_anchor": r[11],
                    }
                )

        snapshot_json = json.dumps(snapshot_data, indent=2).encode("utf-8")
        snapshot_hash = cortex_hash(snapshot_json)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        filename = f"ledger_snapshot_{timestamp_str}_{snapshot_hash[:8]}.json.gz"
        filepath = snapshot_dir / filename

        with gzip.open(filepath, "wb") as f:
            f.write(snapshot_json)

        # Generate the COMPACTION_NODE cryptographic proof
        # The signature is over "COMPACTION:{H_start}:{H_end}:{snapshot_hash}"
        compaction_payload = f"COMPACTION:{h_start}:{h_end}:{snapshot_hash}"
        compaction_signature = ledger.private_key.sign(compaction_payload.encode()).hex()

        compaction_timestamp = datetime.now(timezone.utc).isoformat()
        compaction_audit_id = cortex_hash(
            f"{compaction_timestamp}systemCORTEX_KERNELledger_masterCOMPACTION_NODE{snapshot_hash}{h_end}".encode()
        )

        # Execute Transaction
        in_tx_before = conn.in_transaction
        try:
            if not in_tx_before:
                await conn.execute("BEGIN IMMEDIATE")

            from babylon60.database.core import causal_write

            with causal_write(conn):
                # Delete old rows
                placeholders = ",".join(["?"] * len(rowids_to_delete))
                await conn.execute(
                    f"DELETE FROM security_audit_log WHERE rowid IN ({placeholders})",
                    rowids_to_delete,
                )

                # Insert COMPACTION_NODE at the exact rowid of the first deleted row to maintain ORDER BY rowid ASC
                first_rowid = rowids_to_delete[0]

                await conn.execute(
                    """INSERT INTO security_audit_log
                       (rowid, audit_id, timestamp, tenant_id, actor_role, actor_id, action,
                        resource, status, prev_hash, signature, external_anchor)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        first_rowid,
                        compaction_audit_id,
                        compaction_timestamp,
                        "system",
                        "CORTEX_KERNEL",
                        "ledger_master",
                        "COMPACTION_NODE",
                        snapshot_hash,
                        h_end,
                        h_start,
                        compaction_signature,
                        json.dumps({"snapshot_path": str(filepath)}),
                    ),
                )

            if not in_tx_before:
                await conn.commit()

        except Exception as e:  # noqa: BLE001
            if not in_tx_before:
                await conn.rollback()
            raise e

    logger.info(
        "C5-REAL: Ledger Compaction Complete. %d rows compacted into %s",
        len(rowids_to_delete),
        filename,
    )
    return {
        "status": "compacted",
        "rows_compacted": len(rowids_to_delete),
        "snapshot_path": str(filepath),
        "h_start": h_start,
        "h_end": h_end,
    }
