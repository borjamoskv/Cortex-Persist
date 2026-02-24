"""
CORTEX v8.0 — Sovereign MEJORAlo Ouroboros Daemon.

Replaces loop_mejoralo.sh with a sovereign, cross-platform Python implementation.
Ensures continuous code quality evolution with graceful handling.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from pathlib import Path
from typing import Any

from cortex.cli import get_engine
from cortex.mejoralo.canary import CanaryMonitor
from cortex.mejoralo.engine import MejoraloEngine
from cortex.telemetry.metrics import MetricsRegistry
from cortex.thinking.context_fusion import ContextFusion

logger = logging.getLogger("cortex.mejoralo.daemon")


class MejoraloDaemon:
    """Relentless code quality engine that runs in the background."""

    def __init__(
        self,
        project: str,
        base_path: str | Path,
        scan_interval: int = 1800,  # 30 minutes
        target_score: int = 100,
        metrics: MetricsRegistry | None = None,
        db_path: str | Path | None = None,
    ):
        self.project = project
        self.base_path = Path(base_path).resolve()
        self.scan_interval = scan_interval
        self.target_score = target_score
        self.metrics = metrics or MetricsRegistry()

        # 🛡️ Sovereign Security & Context
        from cortex.config import DEFAULT_DB_PATH

        self.cortex_engine = get_engine(db_path or DEFAULT_DB_PATH)
        self.engine = MejoraloEngine(engine=self.cortex_engine)
        self.canary = CanaryMonitor(self.base_path)
        self.fusion = ContextFusion(self.cortex_engine)
        self._running = False
        self._loop_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the evolutionary loop."""
        if self._running:
            return
        self._running = True
        logger.info(
            "☠️ MEJORAlo Daemon started for project '%s' at %s", self.project, self.base_path
        )
        self._loop_task = asyncio.create_task(self._main_loop())

    async def stop(self) -> None:
        """Graceful shutdown with proper CancelledError propagation."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass  # expected — task was cancelled by us
            self._loop_task = None
        logger.info("Sovereign Daemon: Ouroboros cycle paused.")

    async def _main_loop(self) -> None:
        """Primary execution cycle."""
        while self._running:
            start_time = time.monotonic()
            try:
                await self._execute_cycle()
            except (RuntimeError, OSError, ValueError) as e:
                logger.error("Daemon cycle failure: %s", e, exc_info=True)
                self.metrics.increment("mejoralo_daemon_errors")

            elapsed = time.monotonic() - start_time
            sleep_time = max(0, self.scan_interval - elapsed)

            if self._running:
                logger.debug("Daemon sleeping for %.1f seconds...", sleep_time)
                await asyncio.sleep(sleep_time)

    async def _execute_cycle(self):
        """A single scan + heal cycle with Sovereign Security."""
        logger.info("⚡ Starting MEJORAlo evolutionary wave...")
        self.canary.capture_baselines()

        result = await self.engine.scan(self.project, self.base_path)
        self.metrics.set_gauge("cortex_code_score", result.score)

        if result.score >= self.target_score:
            logger.info("💎 Sovereign Standard maintained (130/100). No action.")
            return

        logger.warning(
            "🚨 Quality Breach (%d < %d). Fetching context...", result.score, self.target_score
        )

        # 4. Memory/KI Context Fusion + Causal Analysis
        fused_context = await self.fusion.fuse_context(
            query=" ".join([d.name for d in result.dimensions if d.score < 7])
            if any(d.score < 7 for d in result.dimensions)
            else "refactoring"
        )
        fused_context = await self._ouroboros_analyze(result, fused_context)

        # 5. Sovereign Healing
        success = await self.engine.heal(
            self.project, self.base_path, self.target_score, result, fused_context=fused_context
        )

        if success:
            logger.info("✅ Healing wave finished.")
            self.metrics.inc("mejoralo_heals_total")
            await self._ouroboros_absorb()

            violations = self.canary.verify()
            if violations:
                for v in violations:
                    logger.error("🛑 SECURITY REGRESSION DETECTED: %s", v)
                    self.metrics.inc("mejoralo_security_violations")
        else:
            logger.error("❌ Healing wave failed or stagnated.")

    async def _ouroboros_analyze(self, result: Any, context: str) -> str:
        """🐍 OUROBOROS-∞ PHASE 1: Causal Reasoning."""
        try:
            from cortex.thinking.orchestra import ThoughtOrchestra
            from cortex.thinking.presets import ThinkingMode

            logger.info("🐍 OUROBOROS-∞: Analyzing causal degradation...")
            async with ThoughtOrchestra() as orchestra:
                prompt = (
                    f"Project {self.project} score: {result.score}. "
                    "Analyze 'shadow debt' and provide strict causal reasoning. "
                    "Technical and concise."
                )
                report = await orchestra.think(prompt, mode=ThinkingMode.DEEP_REASONING)
                return f"{context}\n\n[OUROBOROS CAUSAL DEBT ANALYSIS]\n{report.content}"
        except (RuntimeError, ImportError, OSError) as e:
            logger.error("OUROBOROS-∞ Causal Analysis failed: %s", e)
            return context

    async def _ouroboros_absorb(self):
        """🐍 OUROBOROS-∞ PHASE 2: Pattern Absorption."""
        try:
            from cortex.thinking.orchestra import ThoughtOrchestra
            from cortex.thinking.presets import ThinkingMode

            logger.info("🐍 OUROBOROS-∞: Extracting proven pattern...")
            async with ThoughtOrchestra() as orchestra:
                prompt = (
                    "Extract ONE proven rule that prevents this exact entropy in the future. "
                    "Format it as a direct, strict rule. No filler."
                )
                rule = await orchestra.think(prompt, mode=ThinkingMode.SPEED)

            logger.info("🐍 Pattern Absorbed: %s", rule.content)

            if hasattr(self.cortex_engine, "facts"):
                await self.cortex_engine.facts.store(
                    project=self.project,
                    content=f"OUROBOROS EVOLUTION: {rule.content}",
                    fact_type="decision",
                    source="ouroboros-daemon",
                    confidence="verified",
                    tags=["ouroboros", "evolution"],
                )
        except (RuntimeError, ImportError, OSError) as e:
            logger.error("OUROBOROS-∞ Pattern Absorption failed: %s", e)


async def run_daemon_cli():
    """Entry point for CLI invocation."""
    project = "cortex"
    path = Path.cwd()

    daemon = MejoraloDaemon(project, path)
    _stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.ensure_future(
                _shutdown(daemon, _stop)
            ),
        )

    await daemon.start()
    await _stop.wait()  # block until signal fires — zero CPU


async def _shutdown(daemon: MejoraloDaemon, stop_event: asyncio.Event) -> None:
    """Coordinated graceful shutdown for the daemon CLI."""
    await daemon.stop()
    stop_event.set()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_daemon_cli())
