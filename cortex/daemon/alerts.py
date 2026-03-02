"""MoskvDaemon — Alert handler mixin.

Extracted from core.py to keep file size under 300 LOC.
Each _alert_* method processes results from a specific monitor
and dispatches notifications via the Notifier subsystem.
"""

from __future__ import annotations

import logging
import sys
import time

from cortex.daemon.notifier import Notifier

__all__ = ["AlertHandlerMixin"]

logger = logging.getLogger("moskv-daemon")


class AlertHandlerMixin:
    """Mixin providing all alert dispatch methods for the daemon.

    Requires the host class to implement:
        - _should_alert(key: str) -> bool
        - auto_mejoralo / entropy_monitor attributes (for dispatch)
    """

    # ─── Simple Alerts ────────────────────────────────────────────

    def _alert_sites(self, sites: list) -> None:
        for site in sites:
            if not site.healthy and self._should_alert(f"site:{site.url}"):  # type: ignore[reportAttributeAccessIssue]
                Notifier.alert_site_down(site)

    def _alert_ghosts(self, ghosts: list) -> None:
        for ghost in ghosts:
            if self._should_alert(f"ghost:{ghost.project}"):  # type: ignore[reportAttributeAccessIssue]
                Notifier.alert_stale_project(ghost)

    def _alert_memory(self, alerts: list) -> None:
        for alert in alerts:
            if self._should_alert(f"memory:{alert.file}"):  # type: ignore[reportAttributeAccessIssue]
                logger.warning("Memory file %s is stale", alert.file)

    def _alert_certs(self, certs: list) -> None:
        for cert in certs:
            if self._should_alert(f"cert:{cert.hostname}"):  # type: ignore[reportAttributeAccessIssue]
                logger.warning("SSL certificate for %s expiring soon", cert.hostname)

    def _alert_engine(self, alerts: list) -> None:
        for eh in alerts:
            if self._should_alert(f"engine:{eh.issue}"):  # type: ignore[reportAttributeAccessIssue]
                logger.warning("CORTEX Engine alert for %s", eh.issue)

    def _alert_disk(self, alerts: list) -> None:
        for da in alerts:
            if self._should_alert(f"disk:{da.path}"):  # type: ignore[reportAttributeAccessIssue]
                logger.warning("Disk space low on %s", da.path)

    # ─── Complex Alerts ───────────────────────────────────────────

    def _alert_mejoralo(self, alerts: list) -> None:
        """Sovereign Alert: Unified monitor for MEJORAlo score degradation."""
        for alert in alerts:
            if alert.score >= 50 or not self._should_alert(f"mejoralo:{alert.project}"):  # type: ignore[reportAttributeAccessIssue]
                continue

            logger.warning(
                "Autonomous MEJORAlo scan for %s returned low score: %d/100 (Dead Code: %s)",
                alert.project,
                alert.score,
                alert.dead_code,
            )

            msg = (
                f"Project {alert.project} score: {alert.score}. "
                "Waking up Legion-1 Swarm (400-subagents)."
            )
            Notifier.notify("☢️ MEJORAlo Brutal Mode", msg, sound="Basso")

            # Sovereign Auto-Heal: Dispatch Brutal Scan
            self._dispatch_warm_repair(alert.project, brutal=False if alert.score >= 30 else True)

    def _alert_entropy(self, alerts: list) -> None:
        """Entropy Watchdog: Trigger purge on extreme complexity buildup."""
        for alert in alerts:
            if not self._should_alert(f"entropy:{alert.project}"):  # type: ignore[reportAttributeAccessIssue]
                continue

            logger.warning(
                "ENTROPY-0 ALERTA CRÍTICA: %s tiene complejidad %d/100. %s",
                alert.project,
                alert.complexity_score,
                alert.message,
            )

            is_critical = alert.complexity_score < 30
            title = "☢️ PURGA DE ENTROPÍA (Score < 30)" if is_critical else "⚠️ Alerta de Entropía"
            msg = (
                f"{alert.project}: Invocando /mejoralo --brutal automáticamente."
                if is_critical
                else f"{alert.project} score {alert.complexity_score}. Cuidado."
            )

            Notifier.notify(title, msg, sound="Basso")

            if is_critical:
                logger.info("Auto-invocando /mejoralo --brutal sobre %s", alert.project)
                self._dispatch_warm_repair(alert.project, brutal=True)

    def _dispatch_warm_repair(self, project: str, brutal: bool = False) -> None:
        """Internal Dispatcher: Spawn background Swarm repair processes."""
        try:
            import subprocess

            path_str = self.auto_mejoralo.projects.get(  # type: ignore[reportAttributeAccessIssue]
                project
            ) or self.entropy_monitor.projects.get(project, ".")  # type: ignore[reportAttributeAccessIssue]
            mode = "--brutal" if brutal else "--deep"

            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "cortex.cli",
                    "mejoralo",
                    "scan",
                    project,
                    ".",
                    mode,
                    "--auto-heal",
                ],
                cwd=path_str,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, ValueError, RuntimeError) as e:
            logger.exception("Sovereign Failure: Failed to dispatch Swarm for %s: %s", project, e)

    def _alert_perception(self, alerts: list) -> None:
        for alert in alerts:
            if self._should_alert(f"perception:{alert.project}"):  # type: ignore[reportAttributeAccessIssue]
                logger.info(
                    "👁️ Perception Alert for %s: %s (Emotion: %s, Confidence: %s)",
                    alert.project,
                    alert.intent,
                    alert.emotion,
                    alert.confidence,
                )
                try:
                    Notifier.notify(
                        "👁️ CORTEX Perception", f"{alert.project}: {alert.summary}", sound="Pop"
                    )
                except (OSError, ValueError, RuntimeError) as e:
                    logger.exception("Failed to execute perception notification: %s", e)

    def _alert_neural(self, alerts: list) -> None:
        for alert in alerts:
            if self._should_alert(f"neural:{alert.intent}"):  # type: ignore[reportAttributeAccessIssue]
                logger.info(
                    "🧠 Neural-Bandwidth Sync: %s (Confidence: %s)", alert.intent, alert.confidence
                )
                try:
                    Notifier.notify("🧠 Neural Intent Detected", alert.summary, sound="Glass")
                except (OSError, ValueError, RuntimeError) as e:
                    logger.exception("Failed to execute neural notification: %s", e)

    def _alert_security(self, alerts: list) -> None:
        """Handles security alerts (fraud/anomalies detected by VectorStoreL2)."""
        for alert in alerts:
            # We use the IP address and similarity signature to debounce alerts
            dedup_key = f"security:{alert.ip_address}:{alert.similarity_score}"
            if self._should_alert(dedup_key):  # type: ignore[reportAttributeAccessIssue]
                logger.warning(
                    "🛡️ SECURITY FRAUD ANOMALY %s: %s (Sim: %.2f)",
                    alert.confidence,
                    alert.summary,
                    alert.similarity_score,
                )
                try:
                    message = f"IP: {alert.ip_address}\n{alert.summary}"
                    Notifier.notify("🛡️ Security Alert", message, sound="Basso")
                except (OSError, ValueError, RuntimeError) as e:
                    logger.exception("Failed to execute security notification: %s", e)

    def _alert_compaction(self, alerts: list) -> None:
        """Handler para CompactionAlert."""
        if not alerts:
            return
        for a in alerts:
            key = f"compaction:{a.project}"
            if self._should_alert(key):  # type: ignore[reportAttributeAccessIssue]
                Notifier.notify("Compaction completed", a.message)
                self._last_alerts[key] = time.monotonic()  # type: ignore[reportAttributeAccessIssue]

    def _alert_signals(self, alerts: list) -> None:
        """Handler for SignalAlert."""
        if not alerts:
            return
        for a in alerts:
            msg = f"L2 Reflex: {a.event_type} - {a.message}"
            logger.info("📡 Signal Reactor: %s", msg)
            if self._should_alert(f"signal:{a.event_type}:{a.project or 'global'}"):  # type: ignore[reportAttributeAccessIssue]
                Notifier.notify("CORTEX Reactive Shift", msg)

    def _alert_tombstone(self, alerts: list) -> None:
        """Handler for TombstoneAlert."""
        if not alerts:
            return
        for a in alerts:
            logger.info("💀 Tombstone Sweep: %s", a.message)
            if self._should_alert("tombstone:sweep"):  # type: ignore[reportAttributeAccessIssue]
                Notifier.notify("Garbage Collection", a.message)

    def _alert_cloud_sync(self, alerts: list) -> None:
        """Handler for CloudSyncAlert."""
        if not alerts:
            return
        for a in alerts:
            logger.debug(a.message)
            logger.info("🧠 CORTEX Sleep Cycle: %s", a.message)

    def _flush_timer(self) -> None:
        """Flush accumulated time tracker heartbeats."""
        if not getattr(self, "tracker", None):
            return
        try:
            entries = self.tracker.flush()  # type: ignore[reportAttributeAccessIssue]
            if entries > 0:
                logger.info("TimeTracker: Consolidado %d entradas de tiempo.", entries)
        except Exception as e:
            logger.error("TimeTracker flush error: %s", e)
