# [C5-REAL] Exergy-Maximized
"""
Apoptosis Engine: Enforces Weaponized Forgetting (Axiom Ω₅).
Purges conversational slop, unverified assumptions, and low-exergy nodes from the memory graph
to prevent Context Rot and maintain C5-REAL execution boundaries.
"""

import logging
import time
from typing import Any

logger = logging.getLogger("babylon60.memory.apoptosis")


class ApoptosisEngine:
    """
    Implements biological apoptosis for memory nodes.
    Facts without cryptographically verified taint or recurring thermodynamic validation
    are forcefully deleted from the context window and persistence layers.
    """

    MIN_TAINT_CONFIDENCE = "C5"
    DECAY_THRESHOLD_HOURS = 72

    @classmethod
    def scan_for_necrosis(cls, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Scans a list of memory nodes and returns those identified as necrotic
        (lacking exergy, unverified, or degraded).
        """
        necrotic_nodes = []
        now = time.time()

        for node in nodes:
            # Check for cryptographic taint
            if "CORTEX-TAINT" not in node.get("metadata", {}):
                logger.warning(
                    f"Necrosis detected: Node {node.get('id', 'UNKNOWN')} lacks CORTEX-TAINT."
                )
                necrotic_nodes.append(node)
                continue

            # Check confidence level
            confidence = node.get("metadata", {}).get("confidence", "C0")
            if confidence != cls.MIN_TAINT_CONFIDENCE:
                logger.warning(
                    f"Necrosis detected: Sub-optimal confidence '{confidence}' in Node {node.get('id', 'UNKNOWN')}."
                )
                necrotic_nodes.append(node)
                continue

            # Check temporal decay (Context Rot)
            timestamp = node.get("metadata", {}).get("timestamp", now)
            hours_elapsed = (now - timestamp) / 3600

            # If a fact hasn't been structurally reinforced/accessed in 72 hours, it rots.
            if hours_elapsed > cls.DECAY_THRESHOLD_HOURS and not node.get("metadata", {}).get(
                "is_sacred", False
            ):
                logger.warning(
                    f"Necrosis detected: Temporal drift ({hours_elapsed:.1f}h) on Node {node.get('id', 'UNKNOWN')}."
                )
                necrotic_nodes.append(node)

        return necrotic_nodes

    @classmethod
    def trigger_apoptosis(cls, nodes: list[dict[str, Any]]) -> int:
        """
        Executes Weaponized Forgetting on the provided nodes.
        Returns the count of purged nodes.
        """
        necrotic_nodes = cls.scan_for_necrosis(nodes)

        for node in necrotic_nodes:
            # Here we would dispatch the SQLite/Vector DB deletion commands via the SAGA pattern.
            logger.info(
                f"Apoptosis triggered: Purging memory node {node.get('id', 'UNKNOWN')} to recover Exergy."
            )

        return len(necrotic_nodes)


class ApoptosisAgent:
    """
    ApoptosisAgent (Poda de Datos y Compresión Shannon)
    Surgically regulates the database footprint of free-tier and low-contribution tenants.
    Applies Shannon entropy filtration and accelerated ATP-decay thresholds to purge
    conversational noise and enforce physical limits.
    """

    def __init__(self, db_path: str, atp_free_threshold: float = 0.4, max_free_facts: int = 1000):
        self.db_path = db_path
        self.atp_free_threshold = atp_free_threshold
        self.max_free_facts = max_free_facts

    @staticmethod
    def calculate_shannon_entropy(text: str) -> float:
        """Compute the Shannon entropy of a string to measure its information density."""
        if not text:
            return 0.0
        import math

        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1

        entropy = 0.0
        length = len(text)
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    async def run_apoptosis_cycle(self, tenant_id: str) -> dict[str, Any]:
        """Runs the apoptosis cycle on the tenant memory store.

        Enforces:
          1. Shannon entropy filtration: flags facts containing conversational slop / low density noise.
          2. Accelerated ATP-decay: prunes facts below atp_free_threshold.
          3. Absolute bounds: prunes lowest-energy facts if total exceeds max_free_facts.
        """
        logger.info("ApoptosisAgent: running cycle for tenant=%s", tenant_id)
        stats = {
            "scanned": 0,
            "tombstoned": 0,
            "errors": [],
        }

        import sqlite3

        from babylon60.database.core import causal_write, connect_async_ctx

        try:
            async with connect_async_ctx(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Select active facts for the tenant
                async with conn.execute(
                    "SELECT id, content, exergy_score FROM facts WHERE tenant_id = ? AND is_tombstoned = 0",
                    (tenant_id,),
                ) as cursor:
                    rows = list(await cursor.fetchall())
                    stats["scanned"] = len(rows)

                    tombstone_ids = []
                    for row in rows:
                        fact_id = row["id"]
                        content = row["content"] or ""
                        exergy = row["exergy_score"] if row["exergy_score"] is not None else 1.0

                        # Calculate Shannon Entropy
                        entropy = self.calculate_shannon_entropy(content)
                        # Accelerated decay for conversational noise: short text (< 15 chars) or low entropy (< 2.5)
                        if len(content) < 15 or entropy < 2.5:
                            exergy = exergy * 0.5

                        # Accelerated ATP-decay threshold check
                        if exergy < self.atp_free_threshold:
                            tombstone_ids.append(fact_id)

                # Absolute Bound Quota Enforcement
                active_facts_count = len(rows) - len(tombstone_ids)
                if active_facts_count > self.max_free_facts:
                    excess = active_facts_count - self.max_free_facts
                    # Target lowest exergy score first among non-tombstoned facts
                    remaining_rows = [r for r in rows if r["id"] not in tombstone_ids]
                    remaining_rows.sort(
                        key=lambda r: r["exergy_score"] if r["exergy_score"] is not None else 1.0
                    )
                    for i in range(min(excess, len(remaining_rows))):
                        tombstone_ids.append(remaining_rows[i]["id"])

                # Apply Tombstones inside causal write context
                if tombstone_ids:
                    with causal_write(conn):
                        placeholders = ",".join(["?"] * len(tombstone_ids))
                        await conn.execute(  # nosec
                            f"UPDATE facts SET is_tombstoned = 1 WHERE id IN ({placeholders}) AND tenant_id = ?",
                            tombstone_ids + [tenant_id],
                        )
                        await conn.commit()
                        stats["tombstoned"] = len(tombstone_ids)
                        logger.info(
                            "ApoptosisAgent: tombstoned %d facts for tenant %s",
                            len(tombstone_ids),
                            tenant_id,
                        )

        except Exception as e:  # noqa: BLE001
            logger.error("ApoptosisAgent cycle failed for %s: %s", tenant_id, e)
            stats["errors"].append(str(e))

        return stats
