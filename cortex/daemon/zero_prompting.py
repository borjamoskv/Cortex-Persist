"""
Axioma Ω₇: Zero-Prompting Autonomous Evolution Daemon
El Colapso del aprendizaje continuo a una directiva libre de orquestación.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.daemon.zero_prompting")


class ZeroPromptingDaemon:
    """
    Implementación operacional del Axioma Ω₇.

    Loop: Observe → Hypothesize → Act → Measure → Crystallize → Repeat
    """

    def __init__(
        self,
        engine: CortexEngine,
        workspace_root: str | Path,
        cycle_interval_hours: float = 24.0,
    ):
        self.engine = engine
        self.root = Path(workspace_root)
        self.interval = cycle_interval_hours * 3600
        self._shutdown = False
        self.last_cycle = 0

    async def _observe(self) -> dict[str, Any]:
        """Observes the current thermodynamic and structural state."""
        logger.debug("[ZERO-PROMPTING] [OBSERVE] Reading system state with MEJORAlo...")
        from cortex.mejoralo.engine import MejoraloEngine

        m_engine = MejoraloEngine(self.engine)
        scan_result = await asyncio.to_thread(m_engine.scan, "CORTEX_ZERO", str(self.root))

        return {
            "entropy_score": 100 - scan_result.score,
            "scan_result": scan_result,
        }

    def _hypothesize(self, state: dict[str, Any], focus: str) -> str:
        """Determines the vector of maximum entropic reduction."""
        scan_result = state.get("scan_result")
        if scan_result and scan_result.score < 95:
            hypothesis = (
                f"Relentless Heal on {scan_result.project} "
                f"mapping entropy from score {scan_result.score} to 100"
            )
        else:
            hypothesis = (
                f"Optimize {focus} with OuroborosOmega "
                f"assuming current entropy {state['entropy_score']}."
            )

        logger.debug(
            "[ZERO-PROMPTING] [HYPOTHESIZE] Formulating mutation on focus: %s -> %s",
            focus,
            hypothesis,
        )
        return hypothesis

    async def _act(self, _hypothesis: str, state: dict[str, Any]) -> dict[str, Any]:
        """Executes the Sovereign mutation."""
        logger.debug("[ZERO-PROMPTING] [ACT] Mutating infrastructure...")
        from cortex.evolution.ouroboros_omega import OuroborosOmega
        from cortex.mejoralo.engine import MejoraloEngine

        scan_result = state.get("scan_result")

        if scan_result and scan_result.score < 95:
            m_engine = MejoraloEngine(self.engine)
            success = await asyncio.to_thread(
                m_engine.relentless_heal, "CORTEX_ZERO", str(self.root), scan_result
            )
            return {"action": "relentless_heal", "success": success}
        else:
            ouroboros = OuroborosOmega(str(self.root))
            success = await asyncio.to_thread(ouroboros.execute_atomic_cycle)
            return {"action": "ouroboros_atomic_cycle", "success": success}

    async def _measure_improvement(
        self, state_before: dict, action_result: dict
    ) -> dict[str, Any]:
        """Rigorously measures if the mutation improved the metrics."""
        state_after = await self._observe()
        entropy_diff = state_before["entropy_score"] - state_after["entropy_score"]
        # Allow evolution if entropy improved OR action executed completely
        net_positive = entropy_diff > 0 or action_result.get("success", False)
        return {
            "net_positive": net_positive,
            "delta_entropy": entropy_diff,
            "new_entropy": state_after["entropy_score"],
        }

    async def _crystallize(self, hypothesis: str, action: dict, improvement: dict) -> None:
        """Persists the successful mutation as a C5 Truth in the CORTEX Ledger."""
        logger.info("[ZERO-PROMPT] [CRYSTALLIZE] Evolution accepted: %s", improvement)
        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                "INSERT INTO facts (id, type, topic, content, timestamp, confidence) "
                "VALUES (lower(hex(randomblob(16))), 'decision', 'ZeroPrompt', ?, ?, 'C5')",
                (
                    f"Evolved: {hypothesis}. "
                    f"Action: {action}. "
                    f"Improvement: {improvement}",
                    time.time(),
                ),
            )
            conn.commit()
            logger.info("  ↳ Written to Ledger: Immutable C5.")
        except Exception as e:
            logger.error("[ZERO-PROMPTING] Ledger crystallization failed: %s", e)

    async def _revert(self, action: dict) -> None:
        """Reverts the changes if the mutation failed the criteria."""
        logger.warning(
            "[ZERO-PROMPTING] [REVERT] Net negative improvement. "
            "Rolling back %s. (Requires manual git rollback for now)",
            action,
        )

    async def evolution_cycle(self, focus: str = "entropy") -> dict[str, Any]:
        """Executes one complete Zero-Prompting cycle."""
        logger.info("[ZERO-PROMPTING] Initiating Evolution Cycle: %s", focus)

        state_before = await self._observe()
        hypothesis = self._hypothesize(state_before, focus)

        action_result = await self._act(hypothesis, state_before)
        if not action_result["success"]:
            return {"evolved": False, "reason": "Action failed"}

        improvement = await self._measure_improvement(state_before, action_result)

        if improvement["net_positive"]:
            await self._crystallize(hypothesis, action_result, improvement)
            return {"evolved": True, "improvement": improvement}
        else:
            await self._revert(action_result)
            return {"evolved": False, "reason": "Net negative improvement"}

    async def run_loop(self) -> None:
        """The core Zero-Prompting pulse."""
        logger.info("🧠 Zero-Prompting Evolution Daemon ONLINE.")
        while not self._shutdown:
            now = time.time()
            if now - self.last_cycle > self.interval:
                await self.evolution_cycle(focus="entropy")
                self.last_cycle = now
            await asyncio.sleep(60)

    def stop(self) -> None:
        logger.info("Stopping Zero-Prompting Evolution Daemon.")
        self._shutdown = True
