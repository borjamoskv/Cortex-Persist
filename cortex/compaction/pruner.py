# [C5-REAL] Exergy-Maximized
"""
Merkle Tree Pruner (Compaction Engine)
Consolidates old facts into cryptographically sealed Snapshots to prevent
ledger bloat, maintaining C5-REAL audibility via continuous hash chains.
"""

import hashlib
import logging
from typing import TypedDict

logger = logging.getLogger("cortex.compaction.pruner")

class FactRecord(TypedDict):
    id: str
    payload_hash: str
    taint_token: str
    timestamp: str

class SnapshotSeal(TypedDict):
    snapshot_id: str
    merkle_root: str
    facts_compacted: int
    start_timestamp: str
    end_timestamp: str

class MerklePruner:
    def __init__(self, tolerance_threshold: int = 1000):
        """
        tolerance_threshold: Minimum number of facts required to trigger a compaction leap.
        """
        self.tolerance_threshold = tolerance_threshold

    def _compute_merkle_root(self, hashes: list[str]) -> str:
        """Computes a deterministic Merkle Root from a list of SHA-256 hashes."""
        if not hashes:
            return hashlib.sha256(b"empty").hexdigest()
        
        current_level = hashes
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                h1 = current_level[i]
                h2 = current_level[i+1] if i+1 < len(current_level) else h1
                combined = hashlib.sha256(f"{h1}{h2}".encode()).hexdigest()
                next_level.append(combined)
            current_level = next_level
            
        return current_level[0]

    def crystallize_snapshot(self, facts: list[FactRecord]) -> SnapshotSeal | None:
        """
        Transforms a series of atomic facts into a unified Snapshot Seal.
        """
        if len(facts) < self.tolerance_threshold:
            logger.info(f"Insufficient entropy for compaction: {len(facts)} < {self.tolerance_threshold}")
            return None

        # Sort facts causally (by timestamp) to guarantee deterministic hashing
        sorted_facts = sorted(facts, key=lambda f: f["timestamp"])
        
        hashes = [f["payload_hash"] for f in sorted_facts]
        merkle_root = self._compute_merkle_root(hashes)
        
        snapshot_id = hashlib.sha3_256(f"snapshot:{merkle_root}:{sorted_facts[-1]['timestamp']}".encode()).hexdigest()
        
        seal: SnapshotSeal = {
            "snapshot_id": f"snp_{snapshot_id[:16]}",
            "merkle_root": merkle_root,
            "facts_compacted": len(sorted_facts),
            "start_timestamp": sorted_facts[0]["timestamp"],
            "end_timestamp": sorted_facts[-1]["timestamp"],
        }
        
        logger.info(f"Snapshot Crystallized: {seal['snapshot_id']} | Root: {merkle_root}")
        return seal

    def generate_purge_query(self, facts: list[FactRecord], seal: SnapshotSeal) -> str:
        """
        Generates the idempotent SQL mutation to purge old atomic facts
        and insert the Snapshot Seal into the ledger.
        """
        fact_ids = [f"'{f['id']}'" for f in facts]
        ids_str = ", ".join(fact_ids)
        
        # This is a template to be executed via SAGA Protocol
        sql = f"""
        BEGIN EXCLUSIVE TRANSACTION;
        -- 1. Insert the sealed snapshot
        INSERT INTO cortex_snapshots (snapshot_id, merkle_root, facts_compacted, start_ts, end_ts)
        VALUES ('{seal['snapshot_id']}', '{seal['merkle_root']}', {seal['facts_compacted']}, '{seal['start_timestamp']}', '{seal['end_timestamp']}');
        
        -- 2. Safely purge atomic facts
        DELETE FROM cortex_facts WHERE id IN ({ids_str});
        COMMIT;
        """
        return sql
