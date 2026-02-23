"""Daemon data classes and constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "AGENT_DIR",
    "BUNDLE_ID",
    "CONFIG_FILE",
    "CORTEX_DB",
    "CORTEX_DIR",
    "CertAlert",
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
    "MejoraloAlert",
    "MemoryAlert",
    "NeuralIntentAlert",
    "PerceptionAlert",
    "RETRY_BACKOFF",
    "STATUS_FILE",
    "SecurityAlert",
    "SiteStatus",
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
CORTEX_DIR = Path.home() / ".cortex"
CORTEX_DB = CORTEX_DIR / "cortex.db"
AGENT_DIR = Path.home() / ".agent"
CONFIG_FILE = CORTEX_DIR / "daemon_config.json"
STATUS_FILE = AGENT_DIR / "memory" / "daemon_status.json"
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
    blocked_by: str | None = None


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
    entropy_alerts: list[EntropyAlert] = field(default_factory=list)
    compaction_alerts: list[CompactionAlert] = field(default_factory=list)
    cloud_sync_alerts: list[CloudSyncAlert] = field(default_factory=list)
    perception_alerts: list[PerceptionAlert] = field(default_factory=list)
    neural_alerts: list[NeuralIntentAlert] = field(default_factory=list)
    security_alerts: list[SecurityAlert] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all_healthy(self) -> bool:
        return (
            all(s.healthy for s in self.sites)
            and len(self.stale_ghosts) == 0
            and len(self.memory_alerts) == 0
            and len(self.cert_alerts) == 0
            and len(self.engine_alerts) == 0
            and len(self.disk_alerts) == 0
            and len(self.entropy_alerts) == 0
            and len(self.compaction_alerts) == 0
            and len(self.cloud_sync_alerts) == 0
            and len(self.perception_alerts) == 0
            and len(self.neural_alerts) == 0
            and len(self.security_alerts) == 0
            and len(self.errors) == 0
        )

    def to_dict(self) -> dict:
        return {
            "checked_at": self.checked_at,
            "check_duration_ms": round(self.check_duration_ms, 1),
            "all_healthy": self.all_healthy,
            "sites": [
                {
                    "url": s.url,
                    "healthy": s.healthy,
                    "status_code": s.status_code,
                    "response_ms": round(s.response_ms, 1),
                    "error": s.error,
                    "checked_at": s.checked_at,
                }
                for s in self.sites
            ],
            "stale_ghosts": [
                {
                    "project": g.project,
                    "last_activity": g.last_activity,
                    "hours_stale": round(g.hours_stale, 1),
                    "mood": g.mood,
                    "blocked_by": g.blocked_by,
                }
                for g in self.stale_ghosts
            ],
            "memory_alerts": [
                {
                    "file": m.file,
                    "last_updated": m.last_updated,
                    "hours_stale": round(m.hours_stale, 1),
                }
                for m in self.memory_alerts
            ],
            "cert_alerts": [
                {
                    "hostname": c.hostname,
                    "expires_at": c.expires_at,
                    "days_remaining": c.days_remaining,
                }
                for c in self.cert_alerts
            ],
            "engine_alerts": [{"issue": e.issue, "detail": e.detail} for e in self.engine_alerts],
            "disk_alerts": [
                {"path": d.path, "size_mb": round(d.size_mb, 1), "threshold_mb": d.threshold_mb}
                for d in self.disk_alerts
            ],
            "mejoralo_alerts": [
                {
                    "project": m.project,
                    "score": m.score,
                    "dead_code": m.dead_code,
                    "total_loc": m.total_loc,
                }
                for m in self.mejoralo_alerts
            ],
            "entropy_alerts": [
                {
                    "project": e.project,
                    "file_path": e.file_path,
                    "complexity_score": e.complexity_score,
                    "message": e.message,
                }
                for e in self.entropy_alerts
            ],
            "compaction_alerts": [
                {
                    "project": c.project,
                    "reduction": c.reduction,
                    "deprecated": c.deprecated,
                    "message": c.message,
                }
                for c in self.compaction_alerts
            ],
            "cloud_sync_alerts": [
                {
                    "synced_count": s.synced_count,
                    "last_id": s.last_id,
                    "message": s.message,
                    "latency_ms": round(s.latency_ms, 2),
                }
                for s in self.cloud_sync_alerts
            ],
            "perception_alerts": [
                {
                    "project": p.project,
                    "intent": p.intent,
                    "emotion": p.emotion,
                    "confidence": p.confidence,
                    "summary": p.summary,
                }
                for p in self.perception_alerts
            ],
            "neural_alerts": [
                {
                    "intent": n.intent,
                    "confidence": n.confidence,
                    "trigger": n.trigger,
                    "summary": n.summary,
                }
                for n in self.neural_alerts
            ],
            "security_alerts": [
                {
                    "ip_address": s.ip_address,
                    "payload": s.payload,
                    "similarity_score": round(s.similarity_score, 4),
                    "confidence": s.confidence,
                    "summary": s.summary,
                    "timestamp": s.timestamp,
                }
                for s in self.security_alerts
            ],
            "errors": self.errors,
        }
