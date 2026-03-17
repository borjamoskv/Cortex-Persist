"""Daemon data classes and constants."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

from cortex.core.paths import (
    AGENT_DIR,
    CORTEX_DB,
    CORTEX_DIR,
)
from cortex.core.paths import (
    DAEMON_CONFIG_FILE as CONFIG_FILE,
)
from cortex.core.paths import (
    DAEMON_STATUS_FILE as STATUS_FILE,
)

__all__ = [
    "AGENT_DIR",
    "BUNDLE_ID",
    "CONFIG_FILE",
    "CORTEX_DB",
    "CORTEX_DIR",
    "CertAlert",
    "DriftAlert",
    "CloudSyncAlert",
    "CompactionAlert",
    "DEFAULT_CERT_WARN_DAYS",
    "DEFAULT_COOLDOWN",
    "DEFAULT_DISK_WARN_MB",
    "DEFAULT_INTERVAL",
    "DEFAULT_MEMORY_STALE_HOURS",
    "DEFAULT_RETRIES",
    "DEFAULT_STALE_HOURS",
    "DEFAULT_TIMEOUT",
    "DaemonStatus",
    "DiskAlert",
    "EngineHealthAlert",
    "EntropyAlert",
    "GhostAlert",
    "AetherAlert",
    "MejoraloAlert",
    "MemoryAlert",
    "EvaluationAlert",
    "NeuralIntentAlert",
    "PerceptionAlert",
    "RETRY_BACKOFF",
    "STATUS_FILE",
    "SecurityAlert",
    "SignalAlert",
    "SiteStatus",
    "TombstoneAlert",
    "TrendsAlert",
    "WorkflowAlert",
]

# ─── Constants ────────────────────────────────────────────────────────

DEFAULT_INTERVAL = 300  # 5 minutes
DEFAULT_STALE_HOURS = 48  # ghost projects stale after 48h
DEFAULT_MEMORY_STALE_HOURS = 24  # system.json stale after 24h
DEFAULT_TIMEOUT = 10  # HTTP timeout seconds
DEFAULT_COOLDOWN = 3600  # 1 hour between duplicate alerts
DEFAULT_RETRIES = 1  # HTTP retry count before declaring failure
RETRY_BACKOFF = 2.0  # seconds between retries
DEFAULT_CERT_WARN_DAYS = 14  # warn if SSL expires within 14 days
DEFAULT_DISK_WARN_MB = 500  # warn if cortex dir exceeds 500 MB
BUNDLE_ID = "com.moskv.daemon"

# ─── Data Classes ─────────────────────────────────────────────────────


@dataclass
class SiteStatus:
    """Result of a single site health check."""

    url: str
    healthy: bool
    status_code: int = 0
    response_ms: float = 0.0
    error: str = ""
    checked_at: str = ""


@dataclass
class GhostAlert:
    """A stale project detected from ghosts.json."""

    project: str
    last_activity: str
    hours_stale: float
    mood: str = ""
    blocked_by: Optional[str] = None


@dataclass
class MemoryAlert:
    """CORTEX memory freshness alert."""

    file: str
    last_updated: str
    hours_stale: float


@dataclass
class CertAlert:
    """SSL certificate expiry warning."""

    hostname: str
    expires_at: str
    days_remaining: int


@dataclass
class EngineHealthAlert:
    """CORTEX engine / database health issue."""

    issue: str
    detail: str = ""


@dataclass
class DiskAlert:
    """Disk usage warning for CORTEX data directory."""

    path: str
    size_mb: float
    threshold_mb: float


@dataclass
class MejoraloAlert:
    """MEJORAlo scan result alert for autonomous daemon runs."""

    project: str
    score: int
    dead_code: bool
    total_loc: int


@dataclass
class EvaluationAlert:
    """Alert triggered by the V8 Evaluation Monitor (Stale-Memory or Contradiction)."""

    stale_ratio: float
    stale_count: int
    contradictions_found: int
    message: str


@dataclass
class CompactionAlert:
    """Alert triggered when a project undergoes autonomous compaction."""

    project: str
    reduction: int
    deprecated: int
    message: str


@dataclass
class EntropyAlert:
    """Alerta de incremento de complejidad o deuda técnica (ENTROPY-0)."""

    project: str
    file_path: str
    complexity_score: int
    message: str


@dataclass
class CloudSyncAlert:
    """Alert triggered on successful edge sync to Turso."""

    synced_count: int
    last_id: int
    message: str
    latency_ms: float


@dataclass
class PerceptionAlert:
    """Anomalous or highly confident behavioral pattern detected."""

    project: str
    intent: str
    emotion: str
    confidence: str
    summary: str


@dataclass
class SecurityAlert:
    """Security anomaly detected (fraud attempt, payload mutation, bot)."""

    ip_address: str
    payload: str
    similarity_score: float
    confidence: str
    summary: str
    timestamp: str


@dataclass
class NeuralIntentAlert:
    """Zero-latency intent inferred from macOS implicit context."""

    intent: str
    confidence: str
    trigger: str
    summary: str


@dataclass
class SignalAlert:
    """Alert triggered by a Signal Reactor reflex."""

    event_type: str
    message: str
    project: Optional[str] = None
    payload: dict = field(default_factory=dict)


@dataclass
class TombstoneAlert:
    """Alert triggered when physical tombstone sweep completes."""

    deleted_facts: int
    freed_mb: float
    message: str


@dataclass
class TrendsAlert:
    """Alert for a new trending topic detected by the Trends Oracle."""

    keyword: str
    traffic_volume: str
    geo: str
    category: str
    trend_type: str
    timestamp: str


@dataclass
class AetherAlert:
    """Alert triggered when Aether completes or fails an autonomous task."""

    task_id: str
    title: str
    status: str
    message: str


@dataclass
class WorkflowAlert:
    """Recommendation to deploy a specific workflow based on system state."""

    workflow: str
    reason: str
    confidence: str = "C3"
    priority: int = 5
    tags: list[str] = field(default_factory=list)


@dataclass
class DriftAlert:
    """Alert triggered when L2 vector space topological health degrades."""

    health: float
    centroid_drift: float
    spectral_ratio: float
    n_vectors: int
    message: str


@dataclass
class DaemonStatus:
    """Full daemon check result — persisted to disk."""

    checked_at: str
    check_duration_ms: float = 0.0
    sites: list[SiteStatus] = field(default_factory=list)
    stale_ghosts: list[GhostAlert] = field(default_factory=list)
    memory_alerts: list[MemoryAlert] = field(default_factory=list)
    cert_alerts: list[CertAlert] = field(default_factory=list)
    engine_alerts: list[EngineHealthAlert] = field(default_factory=list)
    disk_alerts: list[DiskAlert] = field(default_factory=list)
    mejoralo_alerts: list[MejoraloAlert] = field(default_factory=list)
    evaluation_alerts: list[EvaluationAlert] = field(default_factory=list)
    entropy_alerts: list[EntropyAlert] = field(default_factory=list)
    compaction_alerts: list[CompactionAlert] = field(default_factory=list)
    cloud_sync_alerts: list[CloudSyncAlert] = field(default_factory=list)
    perception_alerts: list[PerceptionAlert] = field(default_factory=list)
    neural_alerts: list[NeuralIntentAlert] = field(default_factory=list)
    security_alerts: list[SecurityAlert] = field(default_factory=list)
    signal_alerts: list[SignalAlert] = field(default_factory=list)
    tombstone_alerts: list[TombstoneAlert] = field(default_factory=list)
    drift_alerts: list[DriftAlert] = field(default_factory=list)
    trends_alerts: list[TrendsAlert] = field(default_factory=list)
    aether_alerts: list[AetherAlert] = field(default_factory=list)
    workflow_alerts: list[WorkflowAlert] = field(default_factory=list)
    auto_immune_alerts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all_healthy(self) -> bool:
        return all(s.healthy for s in self.sites) and not any(
            (
                self.stale_ghosts,
                self.memory_alerts,
                self.cert_alerts,
                self.engine_alerts,
                self.disk_alerts,
                self.evaluation_alerts,
                self.entropy_alerts,
                self.compaction_alerts,
                self.cloud_sync_alerts,
                self.perception_alerts,
                self.neural_alerts,
                self.security_alerts,
                self.signal_alerts,
                self.tombstone_alerts,
                self.drift_alerts,
                self.trends_alerts,
                self.aether_alerts,
                self.workflow_alerts,
                self.auto_immune_alerts,
                self.errors,
            )
        )

    def to_dict(self) -> dict:
        raw = dataclasses.asdict(self)
        raw["all_healthy"] = self.all_healthy
        raw["check_duration_ms"] = round(self.check_duration_ms, 1)
        return raw
