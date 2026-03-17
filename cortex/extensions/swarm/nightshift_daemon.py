"""CORTEX v8.0 — NightShift Crystal Daemon (Autonomous Knowledge Generation).

Background daemon that periodically discovers targets via KnowledgeRadar,
runs them through the NightShift Pipeline, consolidates existing crystals,
and logs cycle metrics.

Dual-Phase Lifecycle:
    Phase 1 — Acquisition: Radar scan → Pipeline → Forge new crystals
    Phase 2 — Consolidation (REM): Thermometer scan → Purge/Merge/Promote

Axiom Derivations:
    Ω₀ (Self-Reference): If I write it, I execute it — autonomous by design.
    Ω₂ (Entropic Asymmetry): Only targets that reduce uncertainty survive.
    Ω₅ (Antifragile by Default): Each failure forges an antibody.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from cortex.extensions.swarm.knowledge_radar import discover
from cortex.extensions.swarm.nightshift_pipeline import NightShiftPipeline

logger = logging.getLogger("cortex.extensions.swarm.nightshift_daemon")


class NightShiftCrystalDaemon:
    """Autonomous daemon for periodic knowledge crystallization.

    Usage:
        daemon = NightShiftCrystalDaemon(cortex_db=db)
        await daemon.run_cycle()          # Single cycle
        await daemon.daemon_loop()        # Perpetual loop
    """

    def __init__(
        self,
        cortex_db: Optional[Any] = None,
        cooldown_hours: float = 6.0,
        max_crystals: int = 5,
        queue_path: Optional[Path | str] = None,
        encoder: Optional[Any] = None,
        consolidation_dry_run: bool = False,
    ) -> None:
        self._db = cortex_db
        self._cooldown_hours = cooldown_hours
        self._max_crystals = max_crystals
        self._queue_path = queue_path
        self._encoder = encoder
        self._consolidation_dry_run = consolidation_dry_run
        self._stop_event = asyncio.Event()
        self._cycle_history: list[dict[str, Any]] = []
        self._pipeline = NightShiftPipeline()

    # ── Single Cycle ──────────────────────────────────────────────────

    async def run_cycle(self) -> dict[str, Any]:
        """Execute one complete crystal generation cycle.

        Returns:
            Cycle report dict with metrics.
        """
        cycle_start = time.time()
        cycle_id = f"nightshift-{int(cycle_start)}"

        logger.info(
            "🌙 [NIGHTSHIFT] Cycle %s started (max=%d)",
            cycle_id,
            self._max_crystals,
        )

        # 1. Radar scan — discover targets
        try:
            targets = await discover(
                cortex_db=self._db,
                max_targets=self._max_crystals,
                queue_path=self._queue_path,
            )
        except sqlite3.Error as e:
            logger.error("🌙 [NIGHTSHIFT] Radar scan failed (Database error): %s", e)
            report = {
                "cycle_id": cycle_id,
                "status": "radar_failed",
                "error": str(e),
                "crystals": 0,
                "duration_s": time.time() - cycle_start,
            }
            self._cycle_history.append(report)
            return report
        except (ValueError, TypeError) as e:
            logger.error("🌙 [NIGHTSHIFT] Radar scan failed (Validation error): %s", e)
            report = {
                "cycle_id": cycle_id,
                "status": "radar_failed",
                "error": str(e),
                "crystals": 0,
                "duration_s": time.time() - cycle_start,
            }
            self._cycle_history.append(report)
            return report

        if not targets:
            logger.info("🌙 [NIGHTSHIFT] No targets found. Cycle idle.")
            report = {
                "cycle_id": cycle_id,
                "status": "idle",
                "crystals": 0,
                "duration_s": time.time() - cycle_start,
            }
            self._cycle_history.append(report)
            return report

        # 2. Pipeline execution
        try:
            pipeline_result = await self._pipeline.run(targets=targets)
        except sqlite3.Error as e:
            logger.error("🌙 [NIGHTSHIFT] Pipeline failed (Database error): %s", e)
            report = {
                "cycle_id": cycle_id,
                "status": "pipeline_failed",
                "error": str(e),
                "targets_found": len(targets),
                "crystals": 0,
                "duration_s": time.time() - cycle_start,
            }
            self._cycle_history.append(report)
            return report
        except (ValueError, TypeError, RuntimeError) as e:
            logger.error("🌙 [NIGHTSHIFT] Pipeline failed (Execution error): %s", e)
            report = {
                "cycle_id": cycle_id,
                "status": "pipeline_failed",
                "error": str(e),
                "targets_found": len(targets),
                "crystals": 0,
                "duration_s": time.time() - cycle_start,
            }
            self._cycle_history.append(report)
            return report

        # 3. Build cycle report
        crystals_count = pipeline_result.get("crystals_count", 0)
        crystals_forged = pipeline_result.get("crystals_forged", [])
        confidence = pipeline_result.get("confidence", "N/A")
        is_paused = pipeline_result.get("is_paused", False)

        report = {
            "cycle_id": cycle_id,
            "status": "paused" if is_paused else "complete",
            "targets_found": len(targets),
            "crystals": crystals_count,
            "crystals_forged": crystals_forged,
            "confidence": confidence,
            "pipeline_steps": pipeline_result.get("total_steps", 0),
            "duration_s": time.time() - cycle_start,
        }

        if is_paused:
            report["pause_reason"] = pipeline_result.get("pause_reason", "")

        # ── Phase 2: Consolidation (REM) ────────────────────────────
        consolidation_report = await self._run_consolidation(cycle_id)
        if consolidation_report:
            report["consolidation"] = consolidation_report

        self._cycle_history.append(report)

        # 4. Persist cycle report to CORTEX (fire and forget)
        await self._persist_cycle_report(report)

        logger.info(
            "🌙 [NIGHTSHIFT] Cycle %s complete. Crystals=%d, Confidence=%s, "
            "Purged=%d, Merged=%d, Promoted=%d, Duration=%.1fs",
            cycle_id,
            crystals_count,
            confidence,
            consolidation_report.get("purged", 0) if consolidation_report else 0,
            consolidation_report.get("merged", 0) if consolidation_report else 0,
            consolidation_report.get("promoted", 0) if consolidation_report else 0,
            time.time() - cycle_start,
        )

        report["duration_s"] = time.time() - cycle_start
        return report

    # ── Perpetual Loop ────────────────────────────────────────────────

    async def daemon_loop(self) -> None:
        """Run crystallization cycles in a perpetual loop with cooldown.

        Stops when stop() is called.
        """
        logger.info(
            "🌙 [NIGHTSHIFT] Daemon started. Cooldown=%.1fh, Max=%d crystals/cycle",
            self._cooldown_hours,
            self._max_crystals,
        )

        while not self._stop_event.is_set():
            try:
                await self.run_cycle()
            except asyncio.CancelledError:
                logger.info("🌙 [NIGHTSHIFT] Daemon loop cancelled.")
                raise
            except (sqlite3.Error, ValueError, TypeError, RuntimeError) as e:
                logger.error("🌙 [NIGHTSHIFT] Unhandled cycle error: %s", e)

            # Cooldown
            cooldown_s = self._cooldown_hours * 3600
            logger.info(
                "🌙 [NIGHTSHIFT] Sleeping %.1fh until next cycle.",
                self._cooldown_hours,
            )
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=cooldown_s,
                )
                # If we get here, stop was called
                break
            except asyncio.TimeoutError:
                # Normal: cooldown elapsed, time for next cycle
                continue

        logger.info("🌙 [NIGHTSHIFT] Daemon stopped.")

    def stop(self) -> None:
        """Signal the daemon to stop after the current cycle."""
        self._stop_event.set()

    # ── Internal ──────────────────────────────────────────────────────

    async def _persist_cycle_report(self, report: dict[str, Any]) -> None:
        """Persist cycle report to CORTEX as a knowledge fact."""
        if self._db is None:
            return

        try:
            if hasattr(self._db, "store"):
                await self._db.store(
                    fact_type="decision",
                    project="system",
                    content=(
                        f"NightShift cycle {report['cycle_id']}: "
                        f"{report['crystals']} crystals forged, "
                        f"confidence={report.get('confidence', 'N/A')}, "
                        f"duration={report['duration_s']:.1f}s"
                    ),
                    metadata={"nightshift_cycle": report},
                )
        except (sqlite3.Error, AttributeError, ValueError, TypeError) as e:
            logger.warning("🌙 [NIGHTSHIFT] Failed to persist cycle report: %s", e)

    # ── Consolidation Phase ────────────────────────────────────────────

    async def _run_consolidation(self, cycle_id: str) -> Optional[dict[str, Any]]:
        """Execute Phase 2: Crystal consolidation (REM sleep)."""
        if self._db is None:
            return None

        try:
            from cortex.extensions.swarm.crystal_consolidator import consolidate
            from cortex.extensions.swarm.crystal_thermometer import scan_all_crystals

            logger.info("🌙 [NIGHTSHIFT] Phase 2: Consolidation (REM) for %s", cycle_id)

            vitals = await scan_all_crystals(
                db_conn=self._db,
                encoder=self._encoder,
            )

            if not vitals:
                logger.info("🌙 [NIGHTSHIFT] No crystals to consolidate.")
                return {"purged": 0, "merged": 0, "promoted": 0, "total_scanned": 0}

            result = await consolidate(
                db_conn=self._db,
                vitals=vitals,
                dry_run=self._consolidation_dry_run,
            )

            return result.to_dict()

        except (sqlite3.Error, ImportError, ValueError, TypeError) as e:
            logger.error("🌙 [NIGHTSHIFT] Consolidation failed: %s", e)
            return {"error": str(e)}

    # ── Status ────────────────────────────────────────────────────────

    @property
    def history(self) -> list[dict[str, Any]]:
        """Read-only access to cycle history."""
        return list(self._cycle_history)

    @property
    def last_cycle(self) -> Optional[dict[str, Any]]:
        """Most recent cycle report."""
        return self._cycle_history[-1] if self._cycle_history else None

    @property
    def total_crystals(self) -> int:
        """Total crystals generated across all cycles."""
        return sum(c.get("crystals", 0) for c in self._cycle_history)
