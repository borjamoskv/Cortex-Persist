"""MEJORALO-Ω — Sovereign Continuous Script Improvement Agent.

Autonomous agent that runs perpetual Ouroboros cycles:
Scan 13D → Shannon Prioritization → Swarm Heal → Delta-Test → Absorb.

Differs from MejoraloDaemon by using entropy-based targeting,
multi-project support, and exponential backoff on stagnation.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from pathlib import Path
from typing import Any

from cortex.extensions.mejoralo.constants import (
    DAEMON_DEFAULT_TARGET_SCORE,
    STAGNATION_LIMIT,
)
from cortex.extensions.mejoralo.models import ScanResult

logger = logging.getLogger("cortex.extensions.agents.mejoralo_omega")

# ── Constants ──────────────────────────────────────────────────────
DEFAULT_CYCLE_INTERVAL = 120  # seconds between full cycles
BASE_BACKOFF = 30  # base backoff seconds on stagnation
MAX_BACKOFF = 600  # cap backoff at 10 minutes
ENTROPY_SCORE_WEIGHT = 0.6  # weight for scan score in priority
ENTROPY_FINDINGS_WEIGHT = 0.4  # weight for findings count in priority


class MejoraloOmegaAgent:
    """Autonomous continuous improvement agent for scripts and code.

    Loads its configuration from the YAML registry and runs
    perpetual scan → heal → verify → absorb cycles.
    """

    def __init__(
        self,
        project: str,
        base_path: str | Path,
        target_score: int = DAEMON_DEFAULT_TARGET_SCORE,
        cycle_interval: int = DEFAULT_CYCLE_INTERVAL,
        db_path: str | Path | None = None,
    ):
        self.project = project
        self.base_path = Path(base_path).resolve()
        self.target_score = target_score
        self.cycle_interval = cycle_interval
        self._running = False
        self._cycle_count = 0
        self._consecutive_stagnant = 0
        self._score_history: list[int] = []

        # Late-init engine (avoids import-time DB lock)
        self._engine: Any = None
        self._mejoralo: Any = None
        self._db_path = db_path
        self._agent_def: Any = None

    def _ensure_engine(self) -> None:
        """Lazy-initialize CortexEngine and MejoraloEngine."""
        if self._engine is not None:
            return

        from cortex.cli import get_engine
        from cortex.config import DEFAULT_DB_PATH
        from cortex.extensions.mejoralo.engine import MejoraloEngine

        db_val = str(self._db_path) if self._db_path else DEFAULT_DB_PATH
        self._engine = get_engine(db_val)
        self._mejoralo = MejoraloEngine(engine=self._engine)

    def _load_agent_definition(self) -> None:
        """Load the MEJORALO-Ω definition from the agent registry."""
        if self._agent_def is not None:
            return
        try:
            from cortex.extensions.agents.registry import get_agent

            self._agent_def = get_agent("mejoralo_omega")
            if self._agent_def:
                logger.info(
                    "🧬 Loaded agent definition: %s (model: %s)",
                    self._agent_def.name,
                    self._agent_def.resolved_model,
                )
        except ImportError:
            logger.debug("Agent registry not available; using defaults.")

    async def run(self, max_cycles: int | None = None) -> dict[str, Any]:
        """Main execution loop — runs until stopped or max_cycles reached.

        Returns:
            Summary dict with cycle_count, final_score, score_history.
        """
        self._running = True
        self._ensure_engine()
        self._load_agent_definition()

        logger.info(
            "☠️ MEJORALO-Ω activated for '%s' at %s (target: %d)",
            self.project,
            self.base_path,
            self.target_score,
        )

        try:
            while self._running:
                if max_cycles is not None and self._cycle_count >= max_cycles:
                    logger.info("Max cycles (%d) reached. Halting.", max_cycles)
                    break

                self._cycle_count += 1
                start_time = time.monotonic()

                await self._execute_cycle()

                # Adaptive sleep: base interval + exponential backoff on stagnation
                sleep_time = self._compute_sleep(time.monotonic() - start_time)
                if self._running and sleep_time > 0:
                    logger.debug("Sleeping %.1fs before next cycle...", sleep_time)
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.info("MEJORALO-Ω cancelled gracefully.")

        return self._build_summary()

    def stop(self) -> None:
        """Signal the agent to stop after the current cycle."""
        self._running = False
        logger.info("MEJORALO-Ω stop signal received.")

    async def _execute_cycle(self) -> None:
        """Single improvement cycle: scan → prioritize → heal → verify → absorb."""
        from cortex.cli import console

        console.rule(f"[cyan]MEJORALO-Ω Cycle {self._cycle_count}")

        # 1. Scan
        scan_result = self._mejoralo.scan(self.project, self.base_path)
        score_before = scan_result.score
        self._score_history.append(score_before)

        if score_before >= self.target_score:
            console.print(
                f"  [bold green]💎 Target maintained ({score_before}/{self.target_score}). "
                f"Sleeping.[/]"
            )
            self._consecutive_stagnant = 0
            return

        console.print(
            f"  [yellow]🚨 Score {score_before} < {self.target_score}. "
            f"Cycle {self._cycle_count}, stagnation: {self._consecutive_stagnant}[/]"
        )

        # 2. Prioritize targets by Shannon entropy
        targets = self._select_targets(scan_result)
        if not targets:
            console.print("  [dim]No actionable targets found.[/]")
            self._consecutive_stagnant += 1
            return

        console.print(f"  [cyan]🎯 Targeting {len(targets)} files by entropy rank[/]")

        # 3. Heal — escalate level based on stagnation
        level = self._escalation_level()
        success = self._mejoralo.heal(self.project, self.base_path, self.target_score, scan_result)

        # 4. Verify — re-scan
        result_after = self._mejoralo.scan(self.project, self.base_path)
        score_after = result_after.score
        delta = score_after - score_before

        # 5. Record + track stagnation
        self._mejoralo.record_session(
            self.project,
            score_before,
            score_after,
            actions=[f"omega_cycle_{self._cycle_count}_L{level}"],
        )

        if delta <= 0:
            self._consecutive_stagnant += 1
            console.print(
                f"  [yellow]⚠️ Δ{delta:+d} — Stagnation "
                f"{self._consecutive_stagnant}/{STAGNATION_LIMIT}[/]"
            )
        else:
            self._consecutive_stagnant = 0
            console.print(f"  [green]📈 Δ{delta:+d} → {score_after}[/]")

        # 6. Absorb — persist learned pattern on success
        if success and delta > 0:
            await self._absorb_pattern(score_before, score_after)

    def _select_targets(self, scan_result: ScanResult) -> list[tuple[str, float]]:
        """Rank files by Shannon entropy estimate.

        Returns list of (file_path, entropy_score) sorted descending.
        """
        file_entropy: dict[str, float] = {}

        for dim in scan_result.dimensions:
            dim_penalty = max(0, 100 - dim.score) / 100.0
            for finding in dim.findings:
                file_path = self._extract_file(finding)
                if not file_path:
                    continue
                # Accumulate entropy: low score = high entropy + more findings = more entropy
                current = file_entropy.get(file_path, 0.0)
                file_entropy[file_path] = current + dim_penalty * ENTROPY_SCORE_WEIGHT

        # Normalize by findings count
        for dim in scan_result.dimensions:
            for finding in dim.findings:
                fp = self._extract_file(finding)
                if fp and fp in file_entropy:
                    file_entropy[fp] += ENTROPY_FINDINGS_WEIGHT

        ranked = sorted(file_entropy.items(), key=lambda x: x[1], reverse=True)
        return ranked[:10]  # Top 10 entropy targets

    @staticmethod
    def _extract_file(finding: str) -> str | None:
        """Extract file path from a scan finding string."""
        if " -> " in finding or " → " in finding:
            return finding.split(":", 1)[0].strip()
        if " LOC)" in finding:
            return finding.split(" (", 1)[0].strip()
        return None

    def _escalation_level(self) -> int:
        """Determine swarm escalation level from stagnation count."""
        if self._consecutive_stagnant >= STAGNATION_LIMIT * 2:
            return 3
        if self._consecutive_stagnant >= STAGNATION_LIMIT:
            return 2
        return 1

    def _compute_sleep(self, elapsed: float) -> float:
        """Compute adaptive sleep with exponential backoff on stagnation."""
        base = max(0.0, self.cycle_interval - elapsed)
        if self._consecutive_stagnant <= 0:
            return base
        # Exponential backoff: base_backoff * 2^(stagnation - 1), capped
        backoff = min(
            BASE_BACKOFF * math.pow(2, self._consecutive_stagnant - 1),
            MAX_BACKOFF,
        )
        return base + backoff

    async def _absorb_pattern(self, score_before: int, score_after: int) -> None:
        """Persist a learned improvement pattern as a CORTEX fact."""
        try:
            if hasattr(self._engine, "store_sync"):
                self._engine.store_sync(
                    project=self.project,
                    content=(
                        f"MEJORALO-Ω Cycle {self._cycle_count}: "
                        f"Score {score_before} → {score_after} "
                        f"(Δ{score_after - score_before:+d}). "
                        f"Pattern absorbed for entropy prevention."
                    ),
                    fact_type="decision",
                    source="agent:mejoralo-omega",
                    confidence="C4",
                    tags=["mejoralo-omega", "ouroboros", "pattern"],
                )
                logger.info("🐍 Pattern absorbed to CORTEX ledger.")
        except (OSError, RuntimeError, ValueError) as e:
            logger.debug("Pattern absorption skipped: %s", e)

    def _build_summary(self) -> dict[str, Any]:
        """Build a summary of the agent's run."""
        return {
            "agent": "MEJORALO-Ω",
            "project": self.project,
            "cycles_completed": self._cycle_count,
            "final_score": self._score_history[-1] if self._score_history else None,
            "score_history": list(self._score_history),
            "stagnation_at_exit": self._consecutive_stagnant,
            "target_score": self.target_score,
        }


async def run_omega_cli(
    project: str,
    path: str,
    max_cycles: int | None = None,
    interval: int = DEFAULT_CYCLE_INTERVAL,
    target: int = DAEMON_DEFAULT_TARGET_SCORE,
) -> dict[str, Any]:
    """CLI entry point for MEJORALO-Ω."""
    agent = MejoraloOmegaAgent(
        project=project,
        base_path=path,
        target_score=target,
        cycle_interval=interval,
    )
    return await agent.run(max_cycles=max_cycles)
