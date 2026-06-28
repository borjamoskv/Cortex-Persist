# [C5-REAL] Exergy-Maximized
"""
CORTEX - Ouroboros-Ω Gate.
The thermodynamic enforcer for architectural scaling.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("cortex_extensions.gate.ouroboros")


class OuroborosGate:
    """
    Enforces the 3 Laws of Ouroboros-Ω:
    1. Landauer's Razor (Pruning the least dense module)
    2. Latency Conservation (ΔL ≤ 0)
    3. Terminal Recursion (Prompt/Logic auto-condensation)
    """

    def __init__(self, engine_conn: Any):
        self.conn = engine_conn
        self.metrics_key = "ouroboros:entropy_metrics"

    def measure_entropy(self) -> dict[str, Any]:
        """Calculates complexity metrics and signal-to-noise ratio."""
        # Simple heuristic: fact density per project
        total_facts = self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        total_bridges = self.conn.execute(
            "SELECT COUNT(*) FROM facts WHERE fact_type = 'bridge'"
        ).fetchone()[0]
        total_decisions = self.conn.execute(
            "SELECT COUNT(*) FROM facts WHERE fact_type = 'decision'"
        ).fetchone()[0]

        # Signal density
        projects_count = self.conn.execute("SELECT COUNT(DISTINCT project) FROM facts").fetchone()[
            0
        ]

        # SNR calculation
        signal = total_decisions + total_bridges
        # We define noise as the complement of useful facts
        noise = max(1, total_facts - signal)
        snr = signal / noise

        # Absolute Entropy Index: (1/SNR) * (size/1000)
        entropy_idx = (1.0 / (snr + 0.01)) * (total_facts / 1000.0)

        # Landauer's Razor & Exergy
        # X = S * I - T * dS_gen
        # Temperature (T) conceptualized as inversely proportional to SNR
        temperature = max(0.01, 1.0 - snr)
        # Information content (I) ≈ snr, Entropy generated (dS_gen) ≈ total_facts * ln(2) (Landauer)
        exergy = (signal * snr) - (temperature * total_facts * 0.693147)

        return {
            "n_projects": projects_count,
            "total_facts": total_facts,
            "total_bridges": total_bridges,
            "signal_to_noise": round(snr, 3),
            "entropy_index": round(entropy_idx, 4),
            "exergy_score": round(exergy, 4),
            "timestamp": datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
        }

    def identify_dead_weight(self) -> str | None:
        """Identifies the project or module with the lowest importance/density ratio."""
        # Analysis of projects with highest error/bridge ratio
        stats = self.conn.execute("""
            SELECT project,
                   COUNT(*) as total,
                   SUM(CASE WHEN fact_type='error' THEN 1 ELSE 0 END) as errors,
                   SUM(CASE WHEN fact_type='bridge' THEN 1 ELSE 0 END) as bridges
            FROM facts
            GROUP BY project
        """).fetchall()

        if not stats:
            return None

        # Candidates for pruning: many errors, zero bridges
        candidates = []
        for p, total, _, bridges in stats:
            if bridges == 0 and total > 5:
                candidates.append((p, total))

        if candidates:
            # Sort by total facts (higher weight in pruning)
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def trigger_pruning(self, target_project: str):
        """Executes a mass-extinction of a specific project scope."""
        logger.warning("🌀 Ouroboros-Ω: Pruning dead weight project [%s]", target_project)
        # 350/100: Sensory Feedback
        import asyncio

        from cortex.routes.notch_ws import notify_notch_pruning

        asyncio.create_task(notify_notch_pruning())

        # Fetch fact IDs for safe cascading deletion
        cursor = self.conn.execute("SELECT id FROM facts WHERE project = ?", (target_project,))
        fact_ids = [row[0] for row in cursor.fetchall()]
        if fact_ids:
            for i in range(0, len(fact_ids), 900):
                chunk = fact_ids[i : i + 900]
                placeholders = ",".join("?" * len(chunk))
                # Try deleting from tables referencing facts(id), ignore if they don't exist
                tables_to_clean = [
                    "consensus_votes_v2",
                    "consensus_outcomes",
                    "causal_edges",
                    "enrichment_jobs",
                    "fact_vectors",
                    "fact_embeddings",
                    "fact_tags",
                ]
                for table in tables_to_clean:
                    try:
                        self.conn.execute(
                            f"DELETE FROM {table} WHERE fact_id IN ({placeholders})", chunk
                        )
                    except Exception as e:
                        logger.debug(f"Skipping table {table} during pruning: {e}")

            self.conn.execute("DELETE FROM facts WHERE project = ?", (target_project,))
            self.conn.commit()

        # Log scaling decision
        self._log_scaling_event(f"Pruned project {target_project} due to zero bridge density.")

    def _log_scaling_event(self, content: str):
        """Persists architectural scaling decisions."""
        import asyncio
        import time
        from datetime import datetime, timezone

        from cortex.database.core import causal_write, connect_async_ctx
        from cortex.engine.core.fact_store_core import insert_fact_record

        async def _async_log():
            try:
                # Fetch DB path from sync connection
                cursor = self.conn.execute("PRAGMA database_list")
                db_path = None
                for row in cursor.fetchall():
                    if row[1] == "main":
                        db_path = row[2]
                        break
                if not db_path or db_path == "":
                    import os

                    db_path = os.environ.get("CORTEX_DB_PATH", "cortex.db")

                async with connect_async_ctx(db_path) as aconn:
                    with causal_write(aconn):
                        await insert_fact_record(
                            conn=aconn,
                            tenant_id="default",
                            project="cortex",
                            content=content,
                            fact_type="decision",
                            tags=["ouroboros", "scaling", "pruning"],
                            confidence="C5",
                            ts=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                            source="ag:ouroboros",
                            meta=None,
                            tx_id=None,
                        )
                        await aconn.commit()
            except Exception as e:
                import logging

                logging.getLogger("ouroboros").error("Failed to async log scaling event: %s", e)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_async_log())
        except RuntimeError:
            asyncio.run(_async_log())


def get_ouroboros_gate(engine: Any) -> OuroborosGate:
    """Helper to initialize the gate with an engine connection."""
    return OuroborosGate(engine._get_sync_conn())
