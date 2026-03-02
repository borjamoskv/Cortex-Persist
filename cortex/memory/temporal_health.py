"""CORTEX v8 — Temporal Health Scheduler (Sovereign Temporal Hierarchy).

The Axiom: La jerarquía temporal ES la arquitectura.

Running all probes at the same cadence is an architectural error:
  - HIGH-FREQ probes run at the wrong rate → false positives + CPU waste
  - LOW-FREQ probes run too often → O(n·d²) per write → degradación silenciosa

This module implements a multi-frequency scheduler that wraps DriftMonitor
and gates each probe behind a write-count or time-based trigger:

    ┌──────────────┬─────────────┬────────────────┬───────────────────────────┐
    │ Tier         │ Probe       │ Trigger         │ Complexity / call         │
    ├──────────────┼─────────────┼─────────────────┼──────────────────────────│
    │ PULSE        │ centroid    │ Every write     │ O(d) — running mean       │
    │ HEARTBEAT    │ page_hinkley│ Every 10 writes │ O(1) — streaming          │
    │ DIAGNOSTIC   │ spectral_gap│ Every 100 writes│ O(n·d²) — batch           │
    │ DEEP_SCAN    │ intrinsic_dim│ Every 500 writes│ O(n·k·d) — expensive     │
    └──────────────┴─────────────┴─────────────────┴──────────────────────────┘

The running-mean centroid is the only probe that touches every write.
Everything else is amortized. Total overhead per write ≈ O(d).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Final

import numpy as np

from cortex.memory.drift import (
    DriftSignature,
    PageHinkley,
    centroid_drift,
    intrinsic_dimensionality,
    spectral_gap,
)

__all__ = [
    "TemporalHealthScheduler",
    "HealthTier",
    "HealthReport",
    "SchedulerConfig",
]

# Models → temporal_health_models.py (Landauer LOC barrier)
from cortex.memory.temporal_health_models import (  # noqa: E402
    HealthReport,
    HealthTier,
    SchedulerConfig,
)

logger = logging.getLogger("cortex.memory.temporal_health")

# ─── Temporal Health Scheduler ───────────────────────────────────────


class TemporalHealthScheduler:
    """Multi-frequency topological health scheduler.

    Wraps DriftMonitor and gates each probe behind a write-count trigger.
    The running centroid mean is tracked in O(d) per write — the only
    computation that touches every store() call.

    Usage::

        scheduler = TemporalHealthScheduler(
            model_hash=encoder.model_identity_hash,
            signature_dir=Path("~/.cortex/health"),
        )
        scheduler.set_baseline(initial_embeddings)

        # On each write (inside engine.store()):
        report = scheduler.on_write(new_embedding)
        if report.is_alert():
            logger.warning(report.summary())
    """

    __slots__ = (
        "_config",
        "_model_hash",
        "_baseline",
        "_write_count",
        # PULSE: running mean state (O(d) per write)
        "_running_mean",
        "_running_n",
        "_baseline_centroid",
        # HEARTBEAT: Page-Hinkley instance
        "_page_hinkley",
        # DIAGNOSTIC/DEEP: last computed values from baseline
        "_baseline_spectral_gap",
        "_baseline_intrinsic_dim",
        # DEEP: buffer of recent embeddings for expensive probes
        # Capped at deep_scan buffer_size to avoid RAM growth
        "_embedding_buffer",
        "_buffer_maxsize",
        "_signature_dir",
    )

    # How many embeddings to keep in the rolling buffer for batch probes.
    # Must be >= min_vectors_deep_scan. Sovereign default: 2048.
    BUFFER_MAXSIZE: Final[int] = 2048

    def __init__(
        self,
        model_hash: str,
        config: SchedulerConfig | None = None,
        signature_dir: Path | None = None,
    ) -> None:
        self._model_hash = model_hash
        self._config = config or SchedulerConfig()
        self._signature_dir = signature_dir
        self._write_count = 0

        # Running mean state — O(d) memory, updated in O(d) per write
        self._running_mean: np.ndarray | None = None
        self._running_n: int = 0
        self._baseline_centroid: np.ndarray | None = None

        # Streaming Page-Hinkley — O(1) memory, O(1) per update
        self._page_hinkley = PageHinkley(
            threshold=self._config.page_hinkley_threshold,
        )

        # Baseline probe values (set during set_baseline)
        self._baseline_spectral_gap: float | None = None
        self._baseline_intrinsic_dim: float | None = None

        # Rolling buffer for batch probes — bounded RAM
        self._embedding_buffer: list[np.ndarray] = []
        self._buffer_maxsize = self.BUFFER_MAXSIZE

        # Persisted baseline
        self._baseline: DriftSignature | None = None
        if signature_dir:
            sig_path = Path(signature_dir) / "drift_baseline.json"
            loaded = DriftSignature.load(sig_path)
            if loaded and loaded.model_hash == model_hash:
                self._baseline = loaded
                self._baseline_centroid = np.array(loaded.centroid, dtype=np.float32)
                self._baseline_spectral_gap = loaded.spectral_gap
                self._baseline_intrinsic_dim = loaded.intrinsic_dim
                logger.info(
                    "TemporalHealthScheduler: Loaded persisted baseline (n=%d, sg=%.3f, idim=%s)",
                    loaded.n_vectors,
                    loaded.spectral_gap,
                    f"{loaded.intrinsic_dim:.1f}" if loaded.intrinsic_dim else "N/A",
                )

    # ── Public API ────────────────────────────────────────────────────

    def set_baseline(self, embeddings: np.ndarray) -> DriftSignature:
        """Compute and persist the baseline signature (cold calculation).

        Call this once after bulk load or embedder version change.
        The baseline is frozen with the current model_hash.

        Args:
            embeddings: (n, d) float32 — representative sample of the space.

        Returns:
            The frozen DriftSignature.
        """
        if embeddings.ndim != 2 or embeddings.shape[0] < 2:
            raise ValueError(f"Need ≥2 vectors for baseline, got shape {embeddings.shape}")

        centroid = embeddings.mean(axis=0)
        sg = spectral_gap(embeddings)
        idim = intrinsic_dimensionality(embeddings)

        sig = DriftSignature(
            centroid=tuple(float(x) for x in centroid),
            spectral_gap=sg,
            intrinsic_dim=idim,
            n_vectors=embeddings.shape[0],
            model_hash=self._model_hash,
        )

        self._baseline = sig
        self._baseline_centroid = centroid.astype(np.float32)
        self._baseline_spectral_gap = sg
        self._baseline_intrinsic_dim = idim

        # Seed the running mean with the baseline centroid
        self._running_mean = centroid.astype(np.float32).copy()
        self._running_n = embeddings.shape[0]

        # Reset streaming detector on new baseline
        self._page_hinkley.reset()

        # Persist to disk
        if self._signature_dir:
            sig_path = Path(self._signature_dir) / "drift_baseline.json"
            sig.save(sig_path)

        logger.info(
            "TemporalHealthScheduler: Baseline set (n=%d, spectral_gap=%.3f, intrinsic_dim=%s)",
            sig.n_vectors,
            sig.spectral_gap,
            f"{idim:.1f}" if idim is not None else "N/A",
        )
        return sig

    def on_write(self, embedding: np.ndarray) -> HealthReport:
        """Feed one new embedding. Returns a HealthReport for this write.

        This is the only method that MUST be called per-write.
        Complexity: O(d) for the PULSE tier, amortized O(d/N) for HEARTBEAT,
        amortized O(n·d²/100) for DIAGNOSTIC, O(n·k·d/500) for DEEP_SCAN.

        Args:
            embedding: (d,) float32 — the newly stored embedding.

        Returns:
            HealthReport with populated fields for the tiers that fired.
        """
        if embedding.ndim != 1:
            raise ValueError(f"Expected 1-D embedding vector, got shape {embedding.shape}")

        self._write_count += 1
        n = self._write_count

        # Add to rolling buffer (bounded)
        if len(self._embedding_buffer) >= self._buffer_maxsize:
            self._embedding_buffer = self._embedding_buffer[self._buffer_maxsize // 2 :]
        self._embedding_buffer.append(embedding)

        report = HealthReport(write_count=n, tier=[])

        self._run_pulse(embedding, report)

        if n % self._config.heartbeat_every == 0:
            self._run_heartbeat(report)

        if n % self._config.diagnostic_every == 0:
            self._run_diagnostic(n, report)

        if n % self._config.deep_scan_every == 0:
            self._run_deep_scan(n, report)

        report.topological_health = self._compute_composite(report)
        if report.page_hinkley_alert:
            report.topological_health = min(report.topological_health, 0.4)

        if report.alerts:
            logger.warning("TemporalHealthScheduler: %s", report.summary())

        return report

    # ── Tier runners ──────────────────────────────────────────────────

    def _run_pulse(self, embedding: np.ndarray, report: HealthReport) -> None:
        """PULSE tier — O(d) running centroid update, every write."""
        self._update_running_mean(embedding)
        report.running_centroid = self._running_mean
        report.tier.append("pulse")

        if self._baseline_centroid is not None:
            drift = centroid_drift(self._running_mean, self._baseline_centroid)
            report.centroid_drift = drift
            if drift > self._config.centroid_alert_threshold:
                report.alerts.append(
                    f"CENTROID_DRIFT={drift:.4f} > {self._config.centroid_alert_threshold}"
                )
        else:
            report.centroid_drift = 0.0

    def _run_heartbeat(self, report: HealthReport) -> None:
        """HEARTBEAT tier — O(1) Page-Hinkley streaming update."""
        report.tier.append("heartbeat")
        ph_fired = self._page_hinkley.update(report.centroid_drift or 0.0)
        report.page_hinkley_alert = ph_fired
        if ph_fired:
            report.alerts.append("PAGE_HINKLEY_CHANGE_POINT")

    def _run_diagnostic(self, n: int, report: HealthReport) -> None:
        """DIAGNOSTIC tier — O(n·d²) spectral gap, every diagnostic_every writes."""
        buf = self._get_buffer_as_array()
        if buf is None or buf.shape[0] < self._config.min_vectors_diagnostic:
            return

        report.tier.append("diagnostic")
        sg_current = spectral_gap(buf)
        report.spectral_gap_current = sg_current

        if not (self._baseline_spectral_gap and self._baseline_spectral_gap > 1e-10):
            return

        sg_ratio = sg_current / self._baseline_spectral_gap
        report.spectral_gap_ratio = sg_ratio
        thr = self._config.spectral_drop_threshold
        if sg_ratio < thr:
            report.alerts.append(f"SPECTRAL_COLLAPSE ratio={sg_ratio:.3f} < {thr}")
        logger.debug("DIAGNOSTIC write=%d: sg=%.3f ratio=%.3f", n, sg_current, sg_ratio)

    def _run_deep_scan(self, n: int, report: HealthReport) -> None:
        """DEEP_SCAN tier — O(n·k·d) intrinsic dim, every deep_scan_every writes."""
        buf = self._get_buffer_as_array()
        if buf is None or buf.shape[0] < self._config.min_vectors_deep_scan:
            return

        report.tier.append("deep_scan")
        idim_current = intrinsic_dimensionality(buf)
        report.intrinsic_dim_current = idim_current

        if not (
            idim_current is not None
            and self._baseline_intrinsic_dim is not None
            and self._baseline_intrinsic_dim > 1e-10
        ):
            return

        idim_ratio = idim_current / self._baseline_intrinsic_dim
        report.intrinsic_dim_ratio = idim_ratio
        thr_id = self._config.idim_collapse_threshold
        if idim_ratio < thr_id:
            report.alerts.append(f"INTRINSIC_DIM_COLLAPSE ratio={idim_ratio:.3f} < {thr_id}")
        logger.info("DEEP_SCAN write=%d: idim=%.1f ratio=%.3f", n, idim_current, idim_ratio)

    def status(self) -> dict[str, Any]:
        """Current scheduler state — suitable for the CLI `cortex health` command."""
        return {
            "write_count": self._write_count,
            "model_hash": self._model_hash[:12] + "...",
            "baseline_loaded": self._baseline is not None,
            "baseline_n": self._baseline.n_vectors if self._baseline else None,
            "buffer_size": len(self._embedding_buffer),
            "config": {
                "pulse_every": self._config.pulse_every,
                "heartbeat_every": self._config.heartbeat_every,
                "diagnostic_every": self._config.diagnostic_every,
                "deep_scan_every": self._config.deep_scan_every,
            },
            "baseline_metrics": {
                "spectral_gap": self._baseline_spectral_gap,
                "intrinsic_dim": self._baseline_intrinsic_dim,
            }
            if self._baseline
            else None,
        }

    def force_diagnostic(self) -> dict[str, Any]:
        """Force-run the DIAGNOSTIC tier immediately. Useful for CLI / tests."""
        buf = self._get_buffer_as_array()
        if buf is None or buf.shape[0] < self._config.min_vectors_diagnostic:
            return {"error": f"Need ≥{self._config.min_vectors_diagnostic} vectors in buffer"}

        sg = spectral_gap(buf)
        idim = intrinsic_dimensionality(buf)

        sg_ratio = (
            sg / self._baseline_spectral_gap
            if self._baseline_spectral_gap and self._baseline_spectral_gap > 1e-10
            else None
        )
        idim_ratio = (
            idim / self._baseline_intrinsic_dim
            if (idim and self._baseline_intrinsic_dim and self._baseline_intrinsic_dim > 1e-10)
            else None
        )

        return {
            "n_vectors": buf.shape[0],
            "spectral_gap": sg,
            "spectral_gap_ratio": sg_ratio,
            "intrinsic_dim": idim,
            "intrinsic_dim_ratio": idim_ratio,
            "centroid_drift": (
                centroid_drift(self._running_mean, self._baseline_centroid)
                if (self._running_mean is not None and self._baseline_centroid is not None)
                else None
            ),
        }

    # ── Private helpers ───────────────────────────────────────────────

    def _update_running_mean(self, embedding: np.ndarray) -> None:
        """Welford online running mean — O(d), no recomputation."""
        self._running_n += 1
        if self._running_mean is None:
            self._running_mean = embedding.astype(np.float32).copy()
        else:
            # μ_n = μ_{n-1} + (x_n - μ_{n-1}) / n
            delta = embedding.astype(np.float32) - self._running_mean
            self._running_mean += delta / self._running_n

    def _get_buffer_as_array(self) -> np.ndarray | None:
        """Materialize the embedding buffer as a single ndarray.

        Returns None if the buffer is empty.
        """
        if not self._embedding_buffer:
            return None
        return np.stack(self._embedding_buffer, axis=0)

    def _compute_composite(self, report: HealthReport) -> float:
        """Weighted composite health score in [0, 1].

        Only uses signals that are available (non-None).
        """
        components: list[float] = []

        # Centroid drift: healthy if < threshold
        if report.centroid_drift is not None:
            thr = self._config.centroid_alert_threshold
            drift_score = max(0.0, 1.0 - report.centroid_drift / thr)
            components.append(drift_score * 1.5)  # higher weight — most frequent

        # Spectral gap ratio: healthy if close to 1.0
        if report.spectral_gap_ratio is not None:
            sg_score = max(0.0, 1.0 - abs(report.spectral_gap_ratio - 1.0))
            components.append(sg_score)

        # Intrinsic dim ratio: healthy if close to 1.0
        if report.intrinsic_dim_ratio is not None:
            idim_score = max(0.0, 1.0 - abs(report.intrinsic_dim_ratio - 1.0) * 0.5)
            components.append(idim_score)

        if not components:
            return 1.0  # no data → assume healthy (first writes)

        raw = sum(components) / len(components)
        return round(min(1.0, max(0.0, raw)), 4)
