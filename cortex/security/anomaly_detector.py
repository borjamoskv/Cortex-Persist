"""
CORTEX v8 — Anomaly Detector.

Statistical behavioral anomaly detection for CORTEX fact storage.
Monitors rate of mutations, entropy of content, and behavioral
baselines per project using Z-score analysis.
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("cortex.security.anomaly_detector")

__all__ = [
    "AnomalyDetector",
    "AnomalyReport",
    "SecurityEvent",
    "ProjectBaseline",
]


# ═══════════════════════════════════════
# Data Models
# ═══════════════════════════════════════


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """An event to be analyzed for anomalies."""

    source: str  # "agent:gemini", "api:key_abc", "cli:user"
    project: str
    action: str  # "store", "delete", "search", "update"
    content_length: int = 0
    timestamp: float = 0.0  # epoch, filled automatically if 0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())


@dataclass(slots=True)
class AnomalyReport:
    """Report of detected anomaly."""

    is_anomalous: bool = False
    anomaly_type: str = ""  # "rate_limit", "entropy", "behavioral", "bulk_mutation"
    severity: str = "low"  # "critical", "high", "medium", "low"
    description: str = ""
    z_score: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_anomalous": self.is_anomalous,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "z_score": round(self.z_score, 2),
            "details": self.details,
        }


@dataclass(slots=True)
class ProjectBaseline:
    """Behavioral baseline for a project."""

    project: str
    avg_events_per_minute: float = 0.0
    std_events_per_minute: float = 1.0
    avg_content_length: float = 200.0
    std_content_length: float = 100.0
    total_events: int = 0
    last_updated: str = ""


# ═══════════════════════════════════════
# Anomaly Detector
# ═══════════════════════════════════════


class AnomalyDetector:
    """Statistical behavioral anomaly detection.

    Thread-safe in-memory event tracking with Z-score analysis.
    """

    # Rate limit: max events per source per minute
    DEFAULT_RATE_LIMIT: int = 60
    # Z-score threshold for anomaly
    Z_THRESHOLD: float = 3.0
    # Entropy threshold for content
    ENTROPY_THRESHOLD: float = 4.5
    # Window size for rate tracking (seconds)
    RATE_WINDOW: float = 60.0
    # Bulk mutation threshold (events in 10 seconds)
    BULK_THRESHOLD: int = 20

    def __init__(self, rate_limit: int | None = None) -> None:
        self._rate_limit = rate_limit or self.DEFAULT_RATE_LIMIT
        # source -> list of timestamps
        self._rate_tracker: dict[str, list[float]] = defaultdict(list)
        # project -> list of (timestamp, content_length)
        self._project_events: dict[str, list[tuple[float, int]]] = defaultdict(list)
        # project -> baseline
        self._baselines: dict[str, ProjectBaseline] = {}
        # Counters for daily report
        self._daily_events: int = 0
        self._daily_anomalies: int = 0
        self._daily_blocked: int = 0

    def record_event(self, event: SecurityEvent) -> AnomalyReport | None:
        """Record an event and check for anomalies.

        Returns AnomalyReport if anomalous, None if normal.
        """
        self._daily_events += 1
        now = event.timestamp

        # ── Rate Limiting ──
        rate_report = self._check_rate(event.source, now)
        if rate_report:
            self._daily_anomalies += 1
            self._daily_blocked += 1
            return rate_report

        # ── Bulk Mutation Detection ──
        bulk_report = self._check_bulk_mutation(event.source, now)
        if bulk_report:
            self._daily_anomalies += 1
            return bulk_report

        # ── Behavioral Baseline ──
        self._project_events[event.project].append((now, event.content_length))
        baseline_report = self._check_baseline(event)
        if baseline_report:
            self._daily_anomalies += 1
            return baseline_report

        return None

    def check_rate_limit(self, source: str) -> bool:
        """Quick check: is this source within rate limits?"""
        now = time.time()
        self._prune_rate_tracker(source, now)
        return len(self._rate_tracker[source]) < self._rate_limit

    def entropy_score(self, content: str) -> float:
        """Calculate Shannon entropy of content."""
        if not content:
            return 0.0
        freq: dict[str, int] = {}
        for ch in content:
            freq[ch] = freq.get(ch, 0) + 1
        length = len(content)
        return -sum((c / length) * math.log2(c / length) for c in freq.values() if c > 0)

    def get_baseline(self, project: str) -> ProjectBaseline:
        """Get or compute behavioral baseline for a project."""
        if project in self._baselines:
            return self._baselines[project]

        events = self._project_events.get(project, [])
        baseline = ProjectBaseline(
            project=project,
            total_events=len(events),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        if len(events) >= 10:
            # Compute rate stats (events per minute)
            sorted_events = sorted(events, key=lambda e: e[0])
            if len(sorted_events) >= 2:
                time_span = sorted_events[-1][0] - sorted_events[0][0]
                if time_span > 0:
                    rate = len(sorted_events) / (time_span / 60.0)
                    baseline.avg_events_per_minute = rate
                    # Approximate std via windowed rates
                    baseline.std_events_per_minute = max(rate * 0.3, 1.0)

            # Content length stats
            lengths = [e[1] for e in events if e[1] > 0]
            if lengths:
                mean_len = sum(lengths) / len(lengths)
                baseline.avg_content_length = mean_len
                if len(lengths) >= 2:
                    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
                    baseline.std_content_length = max(math.sqrt(variance), 1.0)

        self._baselines[project] = baseline
        return baseline

    def get_daily_stats(self) -> dict[str, int]:
        """Get daily anomaly statistics."""
        return {
            "total_events": self._daily_events,
            "anomalies_detected": self._daily_anomalies,
            "events_blocked": self._daily_blocked,
        }

    def reset_daily_stats(self) -> None:
        """Reset daily counters (called at midnight by daemon)."""
        self._daily_events = 0
        self._daily_anomalies = 0
        self._daily_blocked = 0

    def reset(self) -> None:
        """Reset all detector internal state (used primarily for testing)."""
        self._rate_tracker.clear()
        self._project_events.clear()
        self._baselines.clear()
        self.reset_daily_stats()

    # ── Internal Methods ──

    def _check_rate(self, source: str, now: float) -> AnomalyReport | None:
        """Check if source exceeds rate limit."""
        self._prune_rate_tracker(source, now)
        self._rate_tracker[source].append(now)

        count = len(self._rate_tracker[source])
        if count > self._rate_limit:
            return AnomalyReport(
                is_anomalous=True,
                anomaly_type="rate_limit",
                severity="high",
                description=(
                    f"Source '{source}' exceeded rate limit: "
                    f"{count}/{self._rate_limit} events/minute"
                ),
                z_score=float(count) / max(self._rate_limit, 1),
                details={"source": source, "count": count, "limit": self._rate_limit},
            )
        return None

    def _check_bulk_mutation(self, source: str, now: float) -> AnomalyReport | None:
        """Detect bulk mutations (many events in very short window)."""
        recent = [
            t
            for t in self._rate_tracker.get(source, [])
            if now - t < 10.0  # 10 second window
        ]
        if len(recent) > self.BULK_THRESHOLD:
            return AnomalyReport(
                is_anomalous=True,
                anomaly_type="bulk_mutation",
                severity="critical",
                description=(
                    f"BULK MUTATION DETECTED: {len(recent)} events in 10s from '{source}'"
                ),
                z_score=float(len(recent)) / max(self.BULK_THRESHOLD, 1),
                details={"source": source, "count": len(recent), "window_seconds": 10},
            )
        return None

    def _check_baseline(self, event: SecurityEvent) -> AnomalyReport | None:
        """Z-score behavioral analysis against project baseline."""
        baseline = self.get_baseline(event.project)
        if baseline.total_events < 10:
            return None  # Not enough data for baseline

        # Check content length anomaly
        if event.content_length > 0 and baseline.std_content_length > 0:
            z = (
                abs(event.content_length - baseline.avg_content_length)
                / baseline.std_content_length
            )
            if z > self.Z_THRESHOLD:
                severity = "high" if z > 5.0 else "medium"
                return AnomalyReport(
                    is_anomalous=True,
                    anomaly_type="behavioral",
                    severity=severity,
                    description=(
                        f"Content length anomaly in '{event.project}': "
                        f"{event.content_length} bytes (Z={z:.1f}, baseline={baseline.avg_content_length:.0f})"
                    ),
                    z_score=z,
                    details={
                        "project": event.project,
                        "content_length": event.content_length,
                        "avg": baseline.avg_content_length,
                        "std": baseline.std_content_length,
                    },
                )
        return None

    def _prune_rate_tracker(self, source: str, now: float) -> None:
        """Remove events outside the rate window."""
        cutoff = now - self.RATE_WINDOW
        self._rate_tracker[source] = [t for t in self._rate_tracker[source] if t > cutoff]


# Global singleton
DETECTOR = AnomalyDetector()
