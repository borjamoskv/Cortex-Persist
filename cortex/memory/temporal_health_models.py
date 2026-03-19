"""temporal_health_models — SchedulerConfig, HealthReport, HealthTier.

Extracted from temporal_health.py to satisfy the Landauer LOC barrier (≤500).
Pure data contracts — zero business logic, zero numpy dependency in this file.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

__all__ = ["HealthTier", "SchedulerConfig", "HealthReport"]

# ─── Temporal Tiers ──────────────────────────────────────────────────

HealthTier = Literal["pulse", "heartbeat", "diagnostic", "deep_scan"]


# ─── Configuration ───────────────────────────────────────────────────


@dataclass(frozen=True)
class SchedulerConfig:
    """Controls when each probe fires.

    Defaults encode the sovereign recommendation:
      pulse     → every write   (centroid running mean)
      heartbeat → every 10      (Page-Hinkley streaming)
      diagnostic→ every 100     (spectral gap, O(n·d²))
      deep_scan → every 500     (intrinsic dim, O(n·k·d))
    """

    pulse_every: int = 1  # writes
    heartbeat_every: int = 10  # writes
    diagnostic_every: int = 100  # writes
    deep_scan_every: int = 500  # writes

    # Alert thresholds
    centroid_alert_threshold: float = 0.15  # normalized L2
    spectral_drop_threshold: float = 0.5  # ratio vs baseline
    idim_collapse_threshold: float = 0.3  # ratio: id_dim/baseline drop
    page_hinkley_threshold: float = 50.0  # standard PH lambda

    # Minimum vectors to run diagnostic/deep_scan
    min_vectors_diagnostic: int = 32
    min_vectors_deep_scan: int = 128


# ─── Health Report ───────────────────────────────────────────────────


@dataclass
class HealthReport:
    """Unified health snapshot for a given write count.

    Fields are None when the probe did not fire on this write.
    The `tier` field indicates which tier(s) fired.
    """

    write_count: int
    tier: list[HealthTier]
    timestamp: float = field(default_factory=time.time)

    # PULSE — always populated after write 1
    centroid_drift: float | None = None
    running_centroid: np.ndarray | None = None  # not serialized

    # HEARTBEAT — populated every `heartbeat_every` writes
    page_hinkley_alert: bool = False

    # DIAGNOSTIC — populated every `diagnostic_every` writes
    spectral_gap_current: float | None = None
    spectral_gap_ratio: float | None = None  # vs baseline (1.0 = stable)

    # DEEP_SCAN — populated every `deep_scan_every` writes
    intrinsic_dim_current: float | None = None
    intrinsic_dim_ratio: float | None = None  # vs baseline

    # Composite
    topological_health: float = 1.0  # 0.0 (dead) → 1.0 (perfect)
    alerts: list[str] = field(default_factory=list)
    model_valid: bool = True

    def is_alert(self) -> bool:
        return bool(self.alerts) or self.page_hinkley_alert or not self.model_valid

    def summary(self) -> str:
        tiers = "+".join(self.tier) if self.tier else "none"
        health_pct = f"{self.topological_health * 100:.1f}%"
        alert_str = f" ⚠ {'; '.join(self.alerts)}" if self.alerts else ""
        drift_str = f"{self.centroid_drift:.4f}" if self.centroid_drift is not None else "N/A"
        return (
            f"[write={self.write_count} tier={tiers}] "
            f"health={health_pct} "
            f"drift={drift_str}"
            f"{alert_str}"
        )
