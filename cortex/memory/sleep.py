"""CORTEX v7+ — Sleep Orchestrator (Unified Consolidation Pipeline).

Connects NREM (HippocampalReplay) + REM (AssociativeDreamEngine) into a
single sleep cycle with adaptive calibration feedback.

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │                    SLEEP ORCHESTRATOR                    │
  ├──────────────────────────────────────────────────────────┤
  │  1. Pre-sleep diagnostics  → read MetamemoryMonitor      │
  │  2. NREM Phase             → HippocampalReplay.replay_cycle│
  │  3. REM Phase              → AssociativeDreamEngine.dream │
  │  4. Calibration update     → adjust FOK thresholds (Brier)│
  │  5. Post-sleep report      → emit to Nexus / log         │
  └──────────────────────────────────────────────────────────┘

Biological basis:
  Sleep architecture: NREM (slow-wave, engram compression) → REM
  (theta oscillations, creative association) → brief wake → repeat.
  4–6 cycles per night. CORTEX runs 1 cycle per heartbeat idle window.

Derivation: Ω₅ (Antifragile by Default) + Ω₁ (Multi-Scale Causality)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from cortex.memory.dream import AssociativeDreamEngine
    from cortex.memory.metamemory import MetamemoryMonitor
    from cortex.memory.replay import HippocampalReplay

logger = logging.getLogger("cortex.memory.sleep")

__all__ = [
    "SleepCycleReport",
    "SleepOrchestrator",
]

# ─── Constants ─────────────────────────────────────────────────────────

# Brier score above which we tighten the FOK threshold (we're overconfident)
_BRIER_OVERCONFIDENT: float = 0.25

# Brier score below which we loosen the FOK threshold (we're too conservative)
_BRIER_UNDERCONFIDENT: float = 0.05

# Max adjustment per cycle — prevents runaway drift
_MAX_THRESHOLD_DELTA: float = 0.05

# FOK threshold bounds — never collapse to extremes
_FOK_MIN_THRESHOLD: float = 0.15
_FOK_MAX_THRESHOLD: float = 0.70


# ─── Models ────────────────────────────────────────────────────────────


@dataclass()
class SleepCycleReport:
    """Composite report of a full NREM + REM sleep cycle."""

    tenant_id: str = ""
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0

    # NREM stats
    nrem_merged: int = 0
    nrem_reinforced: int = 0
    nrem_conflicts: int = 0
    nrem_pruned: int = 0
    nrem_duration_ms: float = 0.0

    # REM stats
    rem_clusters_found: int = 0
    rem_bridges_created: int = 0
    rem_engrams_reweighted: int = 0
    rem_duration_ms: float = 0.0

    # Calibration
    brier_before: float = -1.0
    brier_after: float = -1.0
    segmented_brier: dict[str, float] = field(default_factory=dict)
    fok_threshold_before: float = 0.3
    fok_threshold_after: float = 0.3
    threshold_adjusted: bool = False

    # Derived
    knowledge_gaps_detected: int = 0

    @property
    def total_duration_ms(self) -> float:
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at) * 1000
        return self.nrem_duration_ms + self.rem_duration_ms

    @property
    def calibration_improved(self) -> bool:
        """Did Brier score improve (lower = better) during this cycle?"""
        if self.brier_before < 0 or self.brier_after < 0:
            return False
        return self.brier_after < self.brier_before


# ─── Orchestrator ──────────────────────────────────────────────────────


class SleepOrchestrator:
    """Unified NREM + REM sleep cycle orchestrator.

    Designed to be called by the HeartbeatEmitter during idle windows.
    Single entry point: ``run_full_cycle(tenant_id)``.

    Pure composition — no direct DB logic. All state goes through
    the injected engines (adapter pattern).
    """

    def __init__(
        self,
        nrem: HippocampalReplay,
        rem: AssociativeDreamEngine,
        metamemory: MetamemoryMonitor,
        brier_overconfident: float = _BRIER_OVERCONFIDENT,
        brier_underconfident: float = _BRIER_UNDERCONFIDENT,
    ) -> None:
        self._nrem = nrem
        self._rem = rem
        self._metamemory = metamemory
        self._brier_overconfident = brier_overconfident
        self._brier_underconfident = brier_underconfident

    async def run_full_cycle(
        self,
        tenant_id: str,
        hot_engrams: Optional[list[Any]] = None,
    ) -> SleepCycleReport:
        """Execute one complete NREM → REM → Calibration cycle.

        Args:
            tenant_id: Tenant isolation scope.
            hot_engrams: Pre-fetched engrams for NREM phase.
                        If None, NREM will attempt to fetch from vector store.

        Returns:
            SleepCycleReport with full cycle statistics.
        """
        report = SleepCycleReport(
            tenant_id=tenant_id,
            started_at=time.monotonic(),
        )

        # ── Pre-sleep diagnostics ─────────────────────────────────
        report.brier_before = self._metamemory.calibration_score()
        report.fok_threshold_before = self._metamemory._fok_threshold

        # Domain segmentation (Ω₁: Multi-Scale Causality)
        cal_report = self._metamemory.calibration_report()
        report.segmented_brier = cal_report.get("segmented_brier", {})

        gaps_before = self._metamemory.knowledge_gaps()
        report.knowledge_gaps_detected = len(gaps_before)

        logger.info(
            "[SLEEP] Starting cycle for %s. Brier=%.4f, Domains=%d, Gaps=%d",
            tenant_id,
            report.brier_before,
            len(report.segmented_brier),
            report.knowledge_gaps_detected,
        )
        for domain, score in report.segmented_brier.items():
            if score >= 0:
                logger.info("   ↳ Domain [%s]: Brier=%.4f", domain, score)

        # ── Phase 1: NREM ─────────────────────────────────────────
        try:
            nrem_result = await self._nrem.replay_cycle(
                tenant_id=tenant_id,
                hot_engrams=hot_engrams,
            )
            report.nrem_merged = nrem_result.merged
            report.nrem_reinforced = nrem_result.reinforced
            report.nrem_conflicts = nrem_result.conflicts
            report.nrem_pruned = nrem_result.pruned
            report.nrem_duration_ms = nrem_result.duration_ms

            logger.info(
                "[SLEEP] NREM complete: merged=%d reinforced=%d conflicts=%d",
                nrem_result.merged,
                nrem_result.reinforced,
                nrem_result.conflicts,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("[SLEEP] NREM phase failed: %s", exc)

        # ── Phase 2: REM ──────────────────────────────────────────
        try:
            rem_result = await self._rem.dream_cycle(tenant_id=tenant_id)
            report.rem_clusters_found = rem_result.clusters_found
            report.rem_bridges_created = rem_result.bridges_created
            report.rem_engrams_reweighted = rem_result.engrams_reweighted
            report.rem_duration_ms = rem_result.duration_ms

            logger.info(
                "[SLEEP] REM complete: clusters=%d bridges=%d reweighted=%d",
                rem_result.clusters_found,
                rem_result.bridges_created,
                rem_result.engrams_reweighted,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("[SLEEP] REM phase failed: %s", exc)

        # ── Phase 3: Adaptive Calibration ────────────────────────
        delta = self._adaptive_threshold_update()
        report.brier_after = self._metamemory.calibration_score()
        report.fok_threshold_after = self._metamemory._fok_threshold
        report.threshold_adjusted = abs(delta) > 1e-6

        if report.threshold_adjusted:
            logger.info(
                "[SLEEP] FOK threshold adjusted %.3f → %.3f (Δ=%.3f)",
                report.fok_threshold_before,
                report.fok_threshold_after,
                delta,
            )

        # ── Finalize ─────────────────────────────────────────────
        report.ended_at = time.monotonic()
        logger.info(
            "[SLEEP] Cycle complete for %s in %.1fms. Calibration: %.4f → %.4f",
            tenant_id,
            report.total_duration_ms,
            report.brier_before,
            report.brier_after,
        )
        return report

    def _adaptive_threshold_update(self) -> float:
        """Adjust the MetamemoryMonitor's FOK threshold based on Brier score.

        If Brier score is HIGH (overconfident) → raise threshold (be stricter).
        If Brier score is LOW (underconfident) → lower threshold (be looser).
        The delta is capped at MAX_THRESHOLD_DELTA per cycle to prevent oscillation.

        Returns the actual delta applied.

        Derivation: Ω₅ (Antifragile) — calibration failures IMPROVE the system.
        """
        brier = self._metamemory.calibration_score()
        if brier < 0:
            # Insufficient data — no adjustment
            return 0.0

        current = self._metamemory._fok_threshold
        delta = 0.0

        if brier > self._brier_overconfident:
            # We predict high confidence but fail → raise the bar
            delta = min(
                _MAX_THRESHOLD_DELTA,
                (brier - self._brier_overconfident) * 0.5,
            )
        elif brier < self._brier_underconfident:
            # We predict low confidence but succeed → lower the bar
            delta = -min(
                _MAX_THRESHOLD_DELTA,
                (self._brier_underconfident - brier) * 0.5,
            )

        if abs(delta) < 1e-6:
            return 0.0

        new_threshold = max(
            _FOK_MIN_THRESHOLD,
            min(_FOK_MAX_THRESHOLD, current + delta),
        )

        # Direct attribute write — MetamemoryMonitor uses __slots__
        # with mutable _fok_threshold, so this is safe
        self._metamemory._fok_threshold = new_threshold  # noqa: SLF001
        return new_threshold - current

    def __repr__(self) -> str:
        brier = self._metamemory.calibration_score()
        brier_str = f"{brier:.4f}" if brier >= 0 else "n/a"
        return (
            f"SleepOrchestrator("
            f"fok={self._metamemory._fok_threshold:.2f}, "  # noqa: SLF001
            f"brier={brier_str})"
        )
