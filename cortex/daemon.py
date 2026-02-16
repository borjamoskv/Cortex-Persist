"""
CORTEX v4.0 — MOSKV-1 Daemon.

Persistent watchdog that gives MOSKV-1 three capabilities:
1. Persistent Vision: HTTP health checks on monitored URLs
2. Temporal Initiative: Stale project detection from ghosts.json
3. Automatic Memory: CORTEX freshness monitoring

Runs as a launchd agent on macOS, checking every 5 minutes.
Configuration is loaded from ~/.cortex/daemon_config.json when present.
"""

from __future__ import annotations

import json
import sqlite3
import logging
import os
import signal
import ssl
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("moskv-daemon")

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
            "engine_alerts": [
                {
                    "issue": e.issue,
                    "detail": e.detail,
                }
                for e in self.engine_alerts
            ],
            "disk_alerts": [
                {
                    "path": d.path,
                    "size_mb": round(d.size_mb, 1),
                    "threshold_mb": d.threshold_mb,
                }
                for d in self.disk_alerts
            ],
            "errors": self.errors,
        }


# ─── Notifier ─────────────────────────────────────────────────────────


class Notifier:
    """macOS native notifications via osascript."""

    @staticmethod
    def notify(title: str, message: str, sound: str = "Submarine") -> bool:
        """Send a macOS notification. Returns True on success."""
        script = (
            f'display notification "{message}" '
            f'with title "{title}" '
            f'sound name "{sound}"'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("Notification failed: %s", e)
            return False

    @staticmethod
    def alert_site_down(site: SiteStatus) -> None:
        Notifier.notify(
            "⚠️ MOSKV-1 — Site Down",
            f"{site.url} is unreachable: {site.error or f'HTTP {site.status_code}'}",
            sound="Basso",
        )

    @staticmethod
    def alert_stale_project(ghost: GhostAlert) -> None:
        hours = int(ghost.hours_stale)
        Notifier.notify(
            "💤 MOSKV-1 — Proyecto Stale",
            f"{ghost.project} lleva {hours}h sin actividad",
        )

    @staticmethod
    def alert_memory_stale(alert: MemoryAlert) -> None:
        hours = int(alert.hours_stale)
        Notifier.notify(
            "🧠 MOSKV-1 — CORTEX Stale",
            f"{alert.file} sin actualizar ({hours}h). Ejecuta /memoria",
        )


# ─── Site Monitor ─────────────────────────────────────────────────────


class SiteMonitor:
    """HTTP health checker for monitored URLs."""

    def __init__(
        self,
        urls: list[str],
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ):
        self.urls = urls
        self.timeout = timeout
        self.retries = retries

    def check_all(self) -> list[SiteStatus]:
        """Check all URLs. Returns list of SiteStatus."""
        results = []
        for url in self.urls:
            results.append(self._check_one(url))
        return results

    def _check_one(self, url: str) -> SiteStatus:
        """Check a single URL with retry and backoff."""
        now = datetime.now(timezone.utc).isoformat()
        last_error = ""

        for attempt in range(1 + self.retries):
            try:
                start = time.monotonic()
                resp = httpx.get(url, timeout=self.timeout, follow_redirects=True)
                elapsed = (time.monotonic() - start) * 1000

                healthy = 200 <= resp.status_code < 400
                return SiteStatus(
                    url=url,
                    healthy=healthy,
                    status_code=resp.status_code,
                    response_ms=elapsed,
                    checked_at=now,
                    error="" if healthy else f"HTTP {resp.status_code}",
                )
            except httpx.TimeoutException:
                last_error = "timeout"
            except httpx.ConnectError:
                last_error = "connection refused"
            except httpx.HTTPError as e:
                last_error = str(e)[:100]

            if attempt < self.retries:
                logger.debug("Retry %d/%d for %s (%s)", attempt + 1, self.retries, url, last_error)
                time.sleep(RETRY_BACKOFF)

        return SiteStatus(url=url, healthy=False, error=last_error, checked_at=now)


# ─── Ghost Watcher ────────────────────────────────────────────────────


class GhostWatcher:
    """Monitors ghosts.json for stale projects."""

    def __init__(
        self,
        ghosts_path: Path = AGENT_DIR / "memory" / "ghosts.json",
        stale_hours: float = DEFAULT_STALE_HOURS,
    ):
        self.ghosts_path = ghosts_path
        self.stale_hours = stale_hours

    def check(self) -> list[GhostAlert]:
        """Return list of projects that are stale."""
        if not self.ghosts_path.exists():
            return []

        try:
            ghosts = json.loads(self.ghosts_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read ghosts.json: %s", e)
            return []

        now = datetime.now(timezone.utc)
        stale = []

        for project, data in ghosts.items():
            ts = data.get("timestamp", "")
            if not ts:
                continue

            # Skip explicitly blocked projects
            if data.get("blocked_by"):
                continue

            try:
                last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hours = (now - last).total_seconds() / 3600

                if hours > self.stale_hours:
                    stale.append(GhostAlert(
                        project=project,
                        last_activity=ts,
                        hours_stale=hours,
                        mood=data.get("mood", ""),
                        blocked_by=data.get("blocked_by"),
                    ))
            except (ValueError, TypeError):
                continue

        return stale


# ─── Memory Syncer ────────────────────────────────────────────────────


class MemorySyncer:
    """Monitors CORTEX memory files for staleness."""

    def __init__(
        self,
        system_path: Path = AGENT_DIR / "memory" / "system.json",
        stale_hours: float = DEFAULT_MEMORY_STALE_HOURS,
    ):
        self.system_path = system_path
        self.stale_hours = stale_hours

    def check(self) -> list[MemoryAlert]:
        """Return alerts for stale memory files."""
        alerts = []

        if not self.system_path.exists():
            return alerts

        try:
            data = json.loads(self.system_path.read_text())
            ts = data.get("meta", {}).get("last_updated", "")
            if not ts:
                return alerts

            last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours = (now - last).total_seconds() / 3600

            if hours > self.stale_hours:
                alerts.append(MemoryAlert(
                    file="system.json",
                    last_updated=ts,
                    hours_stale=hours,
                ))
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.error("Failed to check system.json: %s", e)

        return alerts


# ─── SSL Certificate Monitor ─────────────────────────────────────────


class CertMonitor:
    """Checks SSL certificate expiry for monitored hostnames."""

    def __init__(
        self,
        hostnames: list[str],
        warn_days: int = DEFAULT_CERT_WARN_DAYS,
    ):
        self.hostnames = hostnames
        self.warn_days = warn_days

    def check(self) -> list[CertAlert]:
        """Return alerts for certs expiring within warn_days."""
        alerts = []
        for hostname in self.hostnames:
            alert = self._check_one(hostname)
            if alert:
                alerts.append(alert)
        return alerts

    def _check_one(self, hostname: str) -> CertAlert | None:
        """Check a single hostname's SSL certificate."""
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=DEFAULT_TIMEOUT) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

            not_after = cert.get("notAfter", "")
            if not not_after:
                return None

            # Parse SSL date format: 'MMM DD HH:MM:SS YYYY GMT'
            expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            expires = expires.replace(tzinfo=timezone.utc)
            days_left = (expires - datetime.now(timezone.utc)).days

            if days_left < self.warn_days:
                return CertAlert(
                    hostname=hostname,
                    expires_at=not_after,
                    days_remaining=days_left,
                )
        except (socket.error, ssl.SSLError, OSError) as e:
            logger.warning("SSL check failed for %s: %s", hostname, e)
        return None


# ─── Engine Health Check ─────────────────────────────────────────────


class EngineHealthCheck:
    """Verifies CORTEX database exists and is accessible."""

    def __init__(self, db_path: Path = CORTEX_DB):
        self.db_path = db_path

    def check(self) -> list[EngineHealthAlert]:
        """Return alerts if CORTEX database is missing or unreadable."""
        alerts = []

        if not self.db_path.exists():
            alerts.append(EngineHealthAlert(
                issue="database_missing",
                detail=f"{self.db_path} not found",
            ))
            return alerts

        if not os.access(self.db_path, os.R_OK):
            alerts.append(EngineHealthAlert(
                issue="database_unreadable",
                detail=f"No read permission on {self.db_path}",
            ))

        # Basic integrity: file should be > 0 bytes
        try:
            size = self.db_path.stat().st_size
            if size == 0:
                alerts.append(EngineHealthAlert(
                    issue="database_empty",
                    detail="Database file is 0 bytes",
                ))
        except OSError as e:
            alerts.append(EngineHealthAlert(
                issue="database_stat_error",
                detail=str(e),
            ))

        return alerts


# ─── Disk Monitor ────────────────────────────────────────────────────


class DiskMonitor:
    """Monitors disk usage of the CORTEX data directory."""

    def __init__(
        self,
        watch_path: Path = CORTEX_DIR,
        threshold_mb: float = DEFAULT_DISK_WARN_MB,
    ):
        self.watch_path = watch_path
        self.threshold_mb = threshold_mb

    def check(self) -> list[DiskAlert]:
        """Return alert if watch_path exceeds threshold."""
        if not self.watch_path.exists():
            return []

        total = 0
        try:
            for f in self.watch_path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        except OSError as e:
            logger.warning("Disk check error: %s", e)
            return []

        size_mb = total / (1024 * 1024)
        if size_mb > self.threshold_mb:
            return [DiskAlert(
                path=str(self.watch_path),
                size_mb=size_mb,
                threshold_mb=self.threshold_mb,
            )]
        return []


# ─── Main Daemon ──────────────────────────────────────────────────────


class MoskvDaemon:
    """MOSKV-1 persistent watchdog.

    Orchestrates all monitors and sends alerts.
    Configuration is loaded from ~/.cortex/daemon_config.json when present.

    Usage:
        daemon = MoskvDaemon()
        daemon.check()           # Run once
        daemon.run(interval=300) # Run forever
    """

    def __init__(
        self,
        sites: list[str] | None = None,
        config_dir: Path = AGENT_DIR / "memory",
        stale_hours: float = DEFAULT_STALE_HOURS,
        memory_stale_hours: float = DEFAULT_MEMORY_STALE_HOURS,
        cooldown: float = DEFAULT_COOLDOWN,
        notify: bool = True,
    ):
        self.notify_enabled = notify
        self.config_dir = config_dir
        self._shutdown = False

        # Load config file if present (sites, stale_hours, etc.)
        file_config = self._load_config()
        resolved_sites = sites or file_config.get("sites", [])

        self.site_monitor = SiteMonitor(resolved_sites)
        self.ghost_watcher = GhostWatcher(
            config_dir / "ghosts.json",
            file_config.get("stale_hours", stale_hours),
        )
        self.memory_syncer = MemorySyncer(
            config_dir / "system.json",
            file_config.get("memory_stale_hours", memory_stale_hours),
        )

        # New monitors (Wave 2)
        cert_hostnames = [
            h.replace("https://", "").replace("http://", "").split("/")[0]
            for h in resolved_sites if h.startswith("https://")
        ]
        self.cert_monitor = CertMonitor(
            cert_hostnames,
            file_config.get("cert_warn_days", DEFAULT_CERT_WARN_DAYS),
        )
        self.engine_health = EngineHealthCheck(
            Path(file_config.get("db_path", str(CORTEX_DB)))
        )
        self.disk_monitor = DiskMonitor(
            Path(file_config.get("watch_path", str(CORTEX_DIR))),
            file_config.get("disk_warn_mb", DEFAULT_DISK_WARN_MB),
        )

        self._last_alerts: dict[str, float] = {}  # cooldown tracker
        self._cooldown = file_config.get("cooldown", cooldown)

    @staticmethod
    def _load_config() -> dict:
        """Load daemon config from ~/.cortex/daemon_config.json if it exists."""
        if not CONFIG_FILE.exists():
            return {}
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load daemon config: %s", e)
            return {}

    def check(self) -> DaemonStatus:
        """Run all checks once. Returns DaemonStatus."""
        check_start = time.monotonic()
        now = datetime.now(timezone.utc).isoformat()
        status = DaemonStatus(checked_at=now)

        # 1. Site checks
        try:
            status.sites = self.site_monitor.check_all()
            for site in status.sites:
                if not site.healthy and self._should_alert(f"site:{site.url}"):
                    Notifier.alert_site_down(site)
        except (httpx.HTTPError, OSError) as e:
            status.errors.append(f"Site monitor error: {e}")
            logger.exception("Site monitor failed")

        # 2. Ghost checks
        try:
            status.stale_ghosts = self.ghost_watcher.check()
            for ghost in status.stale_ghosts:
                if self._should_alert(f"ghost:{ghost.project}"):
                    Notifier.alert_stale_project(ghost)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            status.errors.append(f"Ghost watcher error: {e}")
            logger.exception("Ghost watcher failed")

        # 3. Memory checks
        try:
            status.memory_alerts = self.memory_syncer.check()
            for alert in status.memory_alerts:
                if self._should_alert(f"memory:{alert.file}"):
                    Notifier.alert_memory_stale(alert)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            status.errors.append(f"Memory syncer error: {e}")
            logger.exception("Memory syncer failed")

        # 4. SSL certificate checks
        try:
            status.cert_alerts = self.cert_monitor.check()
            for cert in status.cert_alerts:
                if self._should_alert(f"cert:{cert.hostname}"):
                    Notifier.send(
                        "Certificado SSL próximo a caducar",
                        f"{cert.hostname}: expira en {cert.days_remaining} días",
                    )
        except OSError as e:
            status.errors.append(f"Cert monitor error: {e}")
            logger.exception("Cert monitor failed")

        # 5. Engine health
        try:
            status.engine_alerts = self.engine_health.check()
            for eh in status.engine_alerts:
                if self._should_alert(f"engine:{eh.issue}"):
                    Notifier.send(
                        "CORTEX Engine alerta",
                        f"{eh.issue}: {eh.detail}",
                    )
        except OSError as e:
            status.errors.append(f"Engine health error: {e}")
            logger.exception("Engine health check failed")

        # 6. Disk usage
        try:
            status.disk_alerts = self.disk_monitor.check()
            for da in status.disk_alerts:
                if self._should_alert(f"disk:{da.path}"):
                    Notifier.send(
                        "Espacio en disco alto",
                        f"{da.path}: {da.size_mb:.0f}MB (umbral: {da.threshold_mb:.0f}MB)",
                    )
        except OSError as e:
            status.errors.append(f"Disk monitor error: {e}")
            logger.exception("Disk monitor failed")

        # 7. Sincronización automática de memoria JSON ↔ CORTEX DB
        try:
            from cortex.engine import CortexEngine
            from cortex.sync import sync_memory, export_snapshot, export_to_json
            engine = CortexEngine()
            engine.init_db()

            # Forward: JSON → CORTEX
            sync_result = sync_memory(engine)
            if sync_result.had_changes:
                logger.info(
                    "Sync automático: %d hechos sincronizados",
                    sync_result.total,
                )

            # Reverse: CORTEX → JSON (write-back atómico)
            wb_result = export_to_json(engine)
            if wb_result.had_changes:
                logger.info(
                    "Write-back automático: %d archivos, %d items",
                    wb_result.files_written, wb_result.items_exported,
                )

            # Snapshot: CORTEX → markdown legible
            export_snapshot(engine)

            engine.close()
        except (sqlite3.Error, OSError, json.JSONDecodeError, ValueError) as e:
            status.errors.append(f"Memory sync error: {e}")
            logger.exception("Memory sync failed")

        # Record check duration
        status.check_duration_ms = (time.monotonic() - check_start) * 1000

        # Persist status
        self._save_status(status)

        level = "✅" if status.all_healthy else "⚠️"
        logger.info(
            "%s Check complete in %.0fms: %d sites, %d stale ghosts, %d memory alerts",
            level, status.check_duration_ms,
            len(status.sites), len(status.stale_ghosts), len(status.memory_alerts),
        )

        return status

    def run(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Run checks in a loop until stopped.

        Handles both KeyboardInterrupt (Ctrl+C) and SIGTERM (launchd stop)
        for graceful shutdown.
        """
        def _handle_signal(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s, shutting down gracefully...", sig_name)
            self._shutdown = True

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        logger.info("🚀 MOSKV-1 Daemon starting (interval=%ds)", interval)
        try:
            while not self._shutdown:
                self.check()
                # Sleep in small increments to respond quickly to signals
                for _ in range(interval):
                    if self._shutdown:
                        break
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("MOSKV-1 Daemon stopped")

    def _should_alert(self, key: str) -> bool:
        """Rate-limit duplicate alerts (1 per hour per key)."""
        if not self.notify_enabled:
            return False
        now = time.monotonic()
        last = self._last_alerts.get(key, 0)
        if now - last < self._cooldown:
            return False
        self._last_alerts[key] = now
        return True

    def _save_status(self, status: DaemonStatus) -> None:
        """Persist status to daemon_status.json."""
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATUS_FILE.write_text(
                json.dumps(status.to_dict(), indent=2, ensure_ascii=False)
            )
        except OSError as e:
            logger.error("Failed to save status: %s", e)

    @staticmethod
    def load_status() -> dict | None:
        """Load last daemon status from disk."""
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
