import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from cortex.cuatrida.models import CuatridaMetrics, DecisionNode, Dimension
from cortex.engine_async import AsyncCortexEngine
from cortex.mejoralo.engine import MejoraloEngine

logger = logging.getLogger("cortex.cuatrida.orchestrator")


class CuatridaOrchestrator:
    """
    The Sovereign Orchestrator for the Cuátrida Entity.
    Unifies the 4 dimensions of CORTEX.
    """

    def __init__(self, engine: AsyncCortexEngine):
        self.engine = engine
        self.mejoralo = MejoraloEngine(engine=engine)
        self.metrics = CuatridaMetrics()
        self._last_tx_id: int | None = None

    async def log_decision(
        self,
        project: str,
        intent: str,
        dimension: Dimension,
        metadata: dict[str, Any] | None = None,
        conn: Any = None,
    ) -> DecisionNode:
        """
        Dimension B: Seals a decision into the immutable ledger.
        """
        timestamp = datetime.now().isoformat()
        metadata = metadata or {}

        # Dimension B: Hook into CORTEX ledger.
        # Use provided connection if available to stay in the same transaction.
        if conn:
            from cortex.memory.temporal import now_iso
            from cortex.utils.canonical import canonical_json, compute_tx_hash

            dj = canonical_json(metadata)
            ts = now_iso()

            # Previous hash from chain
            async with conn.execute(
                "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
            ) as cursor:
                prev = await cursor.fetchone()
                ph = prev[0] if prev else "GENESIS"

            th = compute_tx_hash(ph, project, f"cuatrida:{dimension.value}", dj, ts)

            cursor = await conn.execute(
                "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project, f"cuatrida:{dimension.value}", dj, ph, th, ts),
            )
            actual_tx_id = cursor.lastrowid
        else:
            # Standalone fallback
            tx_res = await self.engine.write(
                "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) "
                "VALUES (?, ?, ?, 'GENESIS', 'sha256:standalone_placeholder', ?)",
                (project, f"cuatrida:{dimension.value}", json.dumps(metadata), timestamp),
            )
            actual_tx_id = tx_res.unwrap() if tx_res.is_ok() else 0

        self._last_tx_id = actual_tx_id

        node = DecisionNode(
            tx_id=actual_tx_id,
            project=project,
            intent=intent,
            dimension=dimension,
            metrics=self.metrics,
            timestamp=timestamp,
            causal_link=actual_tx_id,
            metadata=metadata,
        )
        self.metrics.decision_count += 1
        logger.info(f"Sovereign Decision Sealed [{dimension.value}] tx:{actual_tx_id}: {intent}")
        return node

    async def validate_aesthetic(self, project: str, path: str | Path) -> bool:
        """
        Dimension C: The Consul of Honor checks for 130/100 standards.
        """
        scan_result = self.mejoralo.scan(project, path)
        self.metrics.aesthetic_honor = float(scan_result.score)
        is_honorable = scan_result.score >= 90
        await self.log_decision(
            project=project,
            intent=f"Aesthetic Audit: {path}",
            dimension=Dimension.AESTHETIC_SOVEREIGNTY,
            metadata={
                "score": scan_result.score,
                "honorable": is_honorable,
                "total_loc": scan_result.total_loc,
            },
        )
        return is_honorable

    async def oracle_ritual(self, project: str, intent: str, cost_tokens: int) -> float:
        """
        Dimension D: The Oracle Ritual.
        Calculates 'Computational Respect' based on intent utility vs cost.
        """
        self.metrics.oracle_invocations += 1
        current_respect = max(0.1, 1.0 - (cost_tokens / 10000.0))
        self.metrics.computational_respect = (
            self.metrics.computational_respect + current_respect
        ) / 2
        await self.log_decision(
            project=project,
            intent=f"Oracle Invocation: {intent}",
            dimension=Dimension.ETHICAL_MANAGEMENT,
            metadata={
                "cost_tokens": cost_tokens,
                "instant_respect": current_respect,
                "cumulative_respect": self.metrics.computational_respect,
            },
        )
        logger.info(f"Oracle Ritual Completed. Respect: {self.metrics.computational_respect:.2f}")
        return self.metrics.computational_respect

    async def zero_friction_sync(self, project: str) -> dict[str, Any]:
        """
        Dimension A: Zero-Friction Sync.
        Interfaces with ghost-control to ensure the system is in a pre-cognitive state.
        """
        ghost_path = (
            Path.home() / ".gemini" / "antigravity" / "skills" / "ghost-control" / "ghost.py"
        )
        latency = 0.0
        status = "unknown"

        if ghost_path.exists():
            start = datetime.now()
            try:
                subprocess.run(
                    ["python3", str(ghost_path), "status"],
                    capture_output=True,
                    timeout=2.0,
                    check=False,
                )
                latency = (datetime.now() - start).total_seconds() * 1000
                status = "active"
            except (subprocess.SubprocessError, OSError):
                status = "error"

        self.metrics.latency_ms = latency
        # Finitud density increases as latency decreases below 100ms
        self.metrics.finitud_density = max(0.1, min(1.0, 1.0 - (latency / 500.0)))

        metadata = {
            "latency_ms": latency,
            "status": status,
            "density": self.metrics.finitud_density,
        }
        await self.log_decision(
            project=project,
            intent="Zero-Friction State Synchronization",
            dimension=Dimension.ZERO_FRICTION,
            metadata=metadata,
        )
        return metadata
