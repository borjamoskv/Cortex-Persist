"""Daemon monitors: Site, Ghost, Memory, Cert, Engine, Disk."""

from __future__ import annotations

import json
import logging
import os
import socket
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from cortex.daemon.models import (
    AGENT_DIR,
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_CERT_WARN_DAYS,
    DEFAULT_DISK_WARN_MB,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_RETRIES,
    DEFAULT_STALE_HOURS,
    DEFAULT_TIMEOUT,
    RETRY_BACKOFF,
    CertAlert,
    DiskAlert,
    EngineHealthAlert,
    EntropyAlert,
    GhostAlert,
    MejoraloAlert,
    MemoryAlert,
    NeuralIntentAlert,
    PerceptionAlert,
    SiteStatus,
)

__all__ = [
    "AutonomousMejoraloMonitor",
    "CertMonitor",
    "DiskMonitor",
    "EngineHealthCheck",
    "EntropyMonitor",
    "GhostWatcher",
    "MemorySyncer",
    "NeuralIntentMonitor",
    "PerceptionMonitor",
    "SiteMonitor",
]

logger = logging.getLogger("moskv-daemon")


class AutonomousMejoraloMonitor:
    """Runs MEJORAlo scan automatically on configured projects."""

    def __init__(self, projects: dict[str, str], interval_seconds: int = 1800, engine=None):
        self.projects = projects
        self.interval_seconds = interval_seconds
        self._last_runs: dict[str, float] = {}
        self._engine = engine

    def _check_project(
        self,
        project: str,
        path_str: str,
        now: float,
        cortex_engine_cls: Any,
        mejoralo_engine_cls: Any,
    ) -> MejoraloAlert | None:
        """Helper to scan a single project and return an alert if successful."""
        last_run = self._last_runs.get(project, 0)
        if now - last_run < self.interval_seconds:
            return None

        path = Path(path_str).expanduser().resolve()
        if not (path.exists() and path.is_dir()):
            return None

        try:
            if not self._engine:
                self._engine = cortex_engine_cls()
            m = mejoralo_engine_cls(self._engine)
            logger.info("Autonomous MEJORAlo running on %s", project)
            result = m.scan(project, path)

            self._last_runs[project] = now
            return MejoraloAlert(
                project=project,
                score=result.score,
                dead_code=result.dead_code,
                total_loc=result.total_loc,
            )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("Autonomous MEJORAlo failed on %s: %s", project, e)
            return None

    def check(self) -> list[MejoraloAlert]:
        """Run MEJORAlo scan if interval has elapsed."""
        alerts = []
        if not self.projects:
            return alerts

        now = time.monotonic()
        try:
            from cortex.engine import CortexEngine
            from cortex.mejoralo import MejoraloEngine
        except ImportError:
            return alerts

        for project, path_str in self.projects.items():
            alert = self._check_project(project, path_str, now, CortexEngine, MejoraloEngine)
            if alert:
                alerts.append(alert)

        return alerts


class EntropyMonitor:
    """Escaneo en segundo plano de ENTROPY-0 para deuda técnica (X-Ray 13D)."""

    def __init__(
        self,
        projects: dict[str, str],
        interval_seconds: int = 1800,
        threshold: int = 90,
        engine=None,
    ):
        self.projects = projects
        self.interval_seconds = interval_seconds
        self.threshold = threshold
        self._last_runs: dict[str, float] = {}
        self._engine = engine

    def _check_project(
        self,
        project: str,
        path_str: str,
        now: float,
        cortex_engine_cls: Any,
        mejoralo_engine_cls: Any,
    ) -> EntropyAlert | None:
        last_run = self._last_runs.get(project, 0)
        if now - last_run < self.interval_seconds:
            return None

        path = Path(path_str).expanduser().resolve()
        if not (path.exists() and path.is_dir()):
            return None

        try:
            if not self._engine:
                self._engine = cortex_engine_cls()
            m = mejoralo_engine_cls(self._engine)
            logger.debug("ENTROPY-0 scanner over %s", project)
            result = m.scan(project, path, deep=False)

            self._last_runs[project] = now
            if result.score < self.threshold:
                return EntropyAlert(
                    project=project,
                    file_path=str(path),
                    complexity_score=result.score,
                    message=f"Entropía detectada: {result.score}/{self.threshold}",
                )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("ENTROPY-0 monitor failed on %s: %s", project, e)
        return None

    def check(self) -> list[EntropyAlert]:
        """Ejecuta escaneo de entropía y reporta si el score < threshold."""
        alerts = []
        if not self.projects:
            return alerts

        now = time.monotonic()
        try:
            from cortex.engine import CortexEngine
            from cortex.mejoralo import MejoraloEngine
        except ImportError:
            return alerts

        for project, path_str in self.projects.items():
            alert = self._check_project(project, path_str, now, CortexEngine, MejoraloEngine)
            if alert:
                alerts.append(alert)

        return alerts


class SiteMonitor:
    """HTTP health checker for monitored URLs."""

    def __init__(
        self, urls: list[str], timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES
    ):
        self.urls = urls
        self.timeout = timeout
        self.retries = retries

    def check_all(self) -> list[SiteStatus]:
        """Check all URLs. Returns list of SiteStatus."""
        return [self._check_one(url) for url in self.urls]

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
            if not ts or data.get("blocked_by"):
                continue
            try:
                last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hours = (now - last).total_seconds() / 3600
                if hours > self.stale_hours:
                    stale.append(
                        GhostAlert(
                            project=project,
                            last_activity=ts,
                            hours_stale=hours,
                            mood=data.get("mood", ""),
                            blocked_by=data.get("blocked_by"),
                        )
                    )
            except (ValueError, TypeError):
                continue
        return stale


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
                alerts.append(MemoryAlert(file="system.json", last_updated=ts, hours_stale=hours))
        except (OSError, ValueError) as e:
            logger.error("Failed to check system.json: %s", e)
        return alerts


class CertMonitor:
    """Checks SSL certificate expiry for monitored hostnames."""

    def __init__(self, hostnames: list[str], warn_days: int = DEFAULT_CERT_WARN_DAYS):
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
            if not_after:
                expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                expires = expires.replace(tzinfo=timezone.utc)
                days_left = (expires - datetime.now(timezone.utc)).days
                if days_left < self.warn_days:
                    return CertAlert(
                        hostname=hostname, expires_at=not_after, days_remaining=days_left
                    )
        except OSError as e:
            logger.warning("SSL check failed for %s: %s", hostname, e)
        return None


class EngineHealthCheck:
    """Verifies CORTEX database exists and is accessible."""

    def __init__(self, db_path: Path = CORTEX_DB):
        self.db_path = db_path

    def check(self) -> list[EngineHealthAlert]:
        """Return alerts if CORTEX database is missing or unreadable."""
        alerts = []
        if not self.db_path.exists():
            alerts.append(
                EngineHealthAlert(issue="database_missing", detail=f"{self.db_path} not found")
            )
            return alerts
        if not os.access(self.db_path, os.R_OK):
            alerts.append(
                EngineHealthAlert(
                    issue="database_unreadable", detail=f"No read permission on {self.db_path}"
                )
            )
        try:
            size = self.db_path.stat().st_size
            if size == 0:
                alerts.append(
                    EngineHealthAlert(issue="database_empty", detail="Database file is 0 bytes")
                )
        except OSError as e:
            alerts.append(EngineHealthAlert(issue="database_stat_error", detail=str(e)))
        return alerts


class DiskMonitor:
    """Monitors disk usage of the CORTEX data directory."""

    def __init__(self, watch_path: Path = CORTEX_DIR, threshold_mb: float = DEFAULT_DISK_WARN_MB):
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
            return [
                DiskAlert(
                    path=str(self.watch_path), size_mb=size_mb, threshold_mb=self.threshold_mb
                )
            ]
        return []


class PerceptionMonitor:
    """Monitors real-time file activity to infer behavioral events."""

    def __init__(self, workspace: str, interval_seconds: int = 300, engine=None):
        self.workspace = workspace
        self.interval_seconds = interval_seconds
        self._pipeline = None
        self._engine = engine

    async def _get_pipeline(self):
        if not self._pipeline:
            import uuid

            from cortex.engine import CortexEngine
            from cortex.perception import PerceptionPipeline

            if not self._engine:
                self._engine = CortexEngine()
            conn = await self._engine.get_conn()
            session_id = f"daemon-{uuid.uuid4().hex[:8]}"
            self._pipeline = PerceptionPipeline(
                conn=conn,
                session_id=session_id,
                workspace=self.workspace,
                window_s=self.interval_seconds,
            )
            self._pipeline.start()
        return self._pipeline

    async def check_async(self) -> list[PerceptionAlert]:
        """Run one check cycle. If we have a snapshot, return it as alert if confident."""
        alerts = []
        try:
            pipeline = await self._get_pipeline()
            snapshot = await pipeline.tick()

            if snapshot and snapshot.confidence in ("C4", "C5") and snapshot.project:
                alerts.append(
                    PerceptionAlert(
                        project=snapshot.project,
                        intent=snapshot.intent,
                        emotion=snapshot.emotion,
                        confidence=snapshot.confidence,
                        summary=snapshot.summary,
                    )
                )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("PerceptionMonitor failed: %s", e)
        return alerts

    def check(self) -> list[PerceptionAlert]:
        """Synchronous wrapper for check_async."""
        import asyncio

        try:
            return asyncio.run(self.check_async())
        except RuntimeError as e:
            if "running event loop" in str(e):
                # If already inside an event loop, schedule it in the background
                if not hasattr(self, "_bg_tasks"):
                    self._bg_tasks = set()
                task = asyncio.ensure_future(self.check_async())
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)
                return []
            raise


class NeuralIntentMonitor:
    """Monitors active window and clipboard on macOS for intent inference."""

    def __init__(self):
        self._engine = None

    def check(self) -> list[NeuralIntentAlert]:
        alerts = []
        try:
            from cortex.neural import NeuralIntentEngine
            from cortex.sys_platform import is_macos

            if not is_macos():
                return alerts

            if not self._engine:
                self._engine = NeuralIntentEngine()

            context, raw_clip = self._engine.read_context()
            hyp = self._engine.infer_intent(context, raw_clip)
            if hyp:
                alerts.append(
                    NeuralIntentAlert(
                        intent=hyp.intent,
                        confidence=hyp.confidence,
                        trigger=hyp.trigger,
                        summary=hyp.summary,
                    )
                )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("NeuralIntentMonitor failed: %s", e)
        return alerts
