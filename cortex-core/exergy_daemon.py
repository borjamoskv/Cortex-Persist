# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""
Exergy Daemon V1.0 - Sovereign Self-Healing & Health Sentinel.

Performs code hygiene (ruff fix & format), SQLite database maintenance (WAL truncate
& vacuum), ambient context auto-snapshots, and resource optimization.
Alerts via the notification bus if aggregate health drops below 60%.
"""

import os
import sys
import asyncio
import sqlite3
import logging
import subprocess
import shutil
import fcntl
from pathlib import Path

# Add paths for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "cortex-core"))

import cortex.core.config as config
from cortex.extensions.health import HealthCollector, HealthScorer, TrendDetector
from cortex.extensions.notifications.setup import setup_notifications
from cortex.extensions.notifications import get_notification_bus, CortexEvent, EventSeverity

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] EXERGY-DAEMON: %(message)s"
)

LOCK_FILE = "/tmp/cortex_exergy_daemon.lock"


class ExergyDaemon:
    """Sovereign loops checking/correcting code & DB health."""

    def __init__(self, check_interval: int = 21600):
        self.is_running = True
        self.check_interval = check_interval
        self.cycle_count = 0

        # Determine ruff paths
        self.venv_ruff = PROJECT_ROOT / ".venv" / "bin" / "ruff"
        self.ruff_cmd = str(self.venv_ruff) if self.venv_ruff.exists() else shutil.which("ruff")

        # Configure notifications
        try:
            setup_notifications(config._cfg)
            self.bus = get_notification_bus()
            logging.info(
                "Exergy Daemon: Notification bus initialized. Adapters: %s",
                self.bus.adapter_names,
            )
        except Exception as e:
            logging.error("Exergy Daemon: Failed to initialize notifications: %s", e)
            self.bus = None

        self.lock_file = None

    def acquire_lock(self):
        """Acquire a file lock to ensure only one instance is running."""
        try:
            self.lock_file = open(LOCK_FILE, "w")
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logging.info("Exergy Daemon: Lock acquired successfully.")
        except BlockingIOError:
            logging.critical("Exergy Daemon: Another instance is already running. Exiting.")
            sys.exit(1)
        except Exception as e:
            logging.error("Exergy Daemon: Failed to acquire lock: %s", e)

    async def auto_heal_code(self):
        """Runs ruff lint auto-fix and format to eliminate code entropy."""
        if not self.ruff_cmd:
            logging.warning("Exergy Daemon: ruff executable not found. Skipping code auto-healing.")
            return

        logging.info("Exergy Daemon: Starting code auto-healing (ruff fix & format)...")

        # Run ruff check --fix
        try:
            process = await asyncio.create_subprocess_exec(
                self.ruff_cmd,
                "check",
                "--fix",
                ".",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(PROJECT_ROOT),
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logging.info("Exergy Daemon: ruff check --fix completed successfully.")
            else:
                logging.warning(
                    "Exergy Daemon: ruff check exited with code %d. stderr: %s",
                    process.returncode,
                    stderr.decode().strip(),
                )
        except OSError as e:
            logging.error(
                "Exergy Daemon: Process spawn failure during ruff check. "
                "Possible OS file descriptor exhaustion: %s",
                e,
            )
            await self.emit_process_exhaustion_alert("ruff check", e)
        except Exception as e:
            logging.error("Exergy Daemon: Unexpected error during ruff check: %s", e)

        # Run ruff format
        try:
            process = await asyncio.create_subprocess_exec(
                self.ruff_cmd,
                "format",
                ".",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(PROJECT_ROOT),
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logging.info("Exergy Daemon: ruff format completed successfully.")
            else:
                logging.warning(
                    "Exergy Daemon: ruff format exited with code %d. stderr: %s",
                    process.returncode,
                    stderr.decode().strip(),
                )
        except OSError as e:
            logging.error(
                "Exergy Daemon: Process spawn failure during ruff format. "
                "Possible OS file descriptor exhaustion: %s",
                e,
            )
            await self.emit_process_exhaustion_alert("ruff format", e)
        except Exception as e:
            logging.error("Exergy Daemon: Unexpected error during ruff format: %s", e)

    async def auto_heal_db(self):
        """Performs database WAL checkpoint (TRUNCATE) and VACUUM to prevent disk fragmentation."""
        db_path = config.DB_PATH
        logging.info("Exergy Daemon: Running DB maintenance on %s...", db_path)
        
        try:
            loop = asyncio.get_running_loop()
            def _maintenance():
                conn = sqlite3.connect(db_path, timeout=30.0)
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    conn.execute("VACUUM;")
                finally:
                    conn.close()
            await loop.run_in_executor(None, _maintenance)
            logging.info("Exergy Daemon: WAL checkpoint and VACUUM completed successfully.")
        except Exception as e:
            logging.error("Exergy Daemon: Database maintenance failure: %s", e)

    async def auto_heal_context_snapshot(self):
        """Forces context inference and persists a new snapshot to keep temporal alignment metrics green."""
        logging.info("Exergy Daemon: Starting context snapshot generation...")
        try:
            from cortex.cli.common import get_engine
            from cortex.extensions.context.collector import ContextCollector
            from cortex.extensions.context.inference import ContextInference

            engine = get_engine(config.DB_PATH)
            await engine.init_db()
            try:
                async with engine.session() as conn:
                    collector = ContextCollector(
                        conn=conn,
                        max_signals=config.CONTEXT_MAX_SIGNALS,
                        workspace_dir=config.CONTEXT_WORKSPACE_DIR,
                        git_enabled=config.CONTEXT_GIT_ENABLED,
                    )
                    signals = await collector.collect_all()
                    inference = ContextInference(conn=conn)
                    result = await inference.infer_and_persist(signals)
                    logging.info(
                        "Exergy Daemon: Ambient context snapshot persisted. "
                        "Project: %s (Confidence: %s)",
                        result.active_project or "None",
                        result.confidence,
                    )
            finally:
                await engine.close()
        except Exception as e:
            logging.error("Exergy Daemon: Context snapshot generation failed: %s", e)

    async def auto_heal_playwright(self):
        """Kills orphaned ms-playwright-go processes to reclaim system resources."""
        logging.info("Exergy Daemon: Checking and cleaning orphaned playwright processes...")
        try:
            # Check if any processes exist first
            process = await asyncio.create_subprocess_exec(
                "pgrep",
                "-f",
                "ms-playwright-go",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if process.returncode == 0 and stdout.strip():
                pids = stdout.decode().strip().splitlines()
                logging.info(
                    "Exergy Daemon: Found %d orphaned ms-playwright-go processes. Killing them...",
                    len(pids),
                )
                # Run pkill
                pkill_proc = await asyncio.create_subprocess_exec(
                    "pkill",
                    "-f",
                    "ms-playwright-go",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await pkill_proc.communicate()
                logging.info("Exergy Daemon: Orphaned processes terminated.")
            else:
                logging.info("Exergy Daemon: No orphaned playwright processes found.")
        except OSError as e:
            logging.error(
                "Exergy Daemon: Failed to query/pkill processes (possible process spawn limit): %s",
                e,
            )
        except Exception as e:
            logging.error("Exergy Daemon: Playwright cleanup failed: %s", e)

    async def perform_health_assessment(self) -> float:
        """Runs the CORTEX Health Suite, logs to DB, and returns the aggregated score."""
        logging.info("Exergy Daemon: Running system health assessment...")
        
        try:
            loop = asyncio.get_running_loop()
            def _assess():
                collector = HealthCollector(db_path=config.DB_PATH)
                metrics = collector.collect_all()
                return metrics, HealthScorer.score(metrics)
            metrics, score = await loop.run_in_executor(None, _assess)

            logging.info(
                "Exergy Daemon: Aggregate Health Score: %.2f/100 (Grade: %s)",
                score.score,
                score.grade.letter,
            )

            # Persist to SQLite health history table
            try:
                def _persist():
                    trend = TrendDetector()
                    trend.push(score.score)
                    trend.persist_to_db(config.DB_PATH, score.score, score.grade.letter)
                    trend.prune_history(config.DB_PATH, keep_days=30)
                await loop.run_in_executor(None, _persist)
                logging.info("Exergy Daemon: Health score persisted and historical records pruned.")
            except Exception as trend_err:
                logging.warning("Exergy Daemon: Failed to update health history database: %s", trend_err)
            # Print detail of each metric
            for m in metrics:
                logging.info("  Metric '%s': %.2f (%s)", m.name, m.value, m.description)

            # Alert if health < 60%
            if score.score < 60.0:
                await self.emit_health_alert(score)

            return score.score
        except Exception as e:
            logging.error("Exergy Daemon: Health assessment crash: %s", e)
            return 0.0

    async def emit_health_alert(self, score):
        """Dispatches a warning event through the NotificationBus."""
        if not self.bus:
            logging.warning("Exergy Daemon: Notification bus not available. Alert dropped.")
            return

        degraded_metrics = []
        for m in score.metrics:
            if m.value < 0.8:
                degraded_metrics.append(
                    f"• {m.name}: {m.value:.2f} ({m.description or 'No desc'}) - "
                    f"Remediation: {m.remediation or 'N/A'}"
                )

        metrics_text = "\n".join(degraded_metrics) if degraded_metrics else "None"

        event = CortexEvent(
            severity=EventSeverity.CRITICAL if score.score < 40.0 else EventSeverity.WARNING,
            title=f"CORTEX Health Alert: Grade {score.grade.letter} ({score.score:.1f}/100)",
            body=(
                f"CORTEX ecosystem health has dropped below the 60% SLA threshold.\n\n"
                f"Aggregated Score: {score.score:.1f}/100\n"
                f"Grade: {score.grade.letter} {score.grade.emoji}\n\n"
                f"Degraded Subsystems:\n{metrics_text}"
            ),
            source="exergy_daemon",
            project="cortex-persist",
        )

        await self.bus.emit(event)
        logging.info("Exergy Daemon: Dispatched health alert through notification bus.")

    async def emit_process_exhaustion_alert(self, action_name: str, error: Exception):
        """Sends a critical alert if process execution fails due to OS limits (e.g. EMFILE)."""
        if not self.bus:
            return

        event = CortexEvent(
            severity=EventSeverity.CRITICAL,
            title="Exergy Daemon: OS Process Limit Exhaustion",
            body=(
                f"Failed to execute '{action_name}' due to OS process spawn limits "
                f"(Too many open files / process limit).\n\n"
                f"Exception: {error}\n"
                f"Immediate action required: check active FDs and system limits via 'ulimit -n'."
            ),
            source="exergy_daemon",
            project="cortex-persist",
        )
        await self.bus.emit(event)

    async def run(self):
        """Main daemon loop executing every check_interval seconds."""
        self.acquire_lock()
        logging.info(
            "Exergy Daemon: Starting sovereign loop. Interval: %d seconds.", self.check_interval
        )

        while self.is_running:
            self.cycle_count += 1
            logging.info("Exergy Daemon: Starting self-healing cycle #%d...", self.cycle_count)

            # Step 1: Auto-heal code formatting and styling
            await self.auto_heal_code()

            # Step 2: Auto-heal databases (vacuum, checkpoints)
            await self.auto_heal_db()

            # Step 3: Auto-heal process hygiene
            await self.auto_heal_playwright()

            # Step 4: Auto-heal context (generate new context snapshot if necessary)
            await self.auto_heal_context_snapshot()

            # Step 5: Check health of the system
            await self.perform_health_assessment()

            logging.info(
                "Exergy Daemon: Cycle #%d completed. Sleeping for %d seconds...",
                self.cycle_count,
                self.check_interval,
            )

            # Sleep using asyncio.sleep
            await asyncio.sleep(self.check_interval)

    def stop(self):
        """Decommissions the daemon and releases resources."""
        self.is_running = False
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except Exception:
                pass
        logging.info("Exergy Daemon: Stopped safely.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run CORTEX Exergy Daemon.")
    parser.add_argument(
        "--interval",
        type=int,
        default=21600,
        help="Check interval in seconds (default: 21600 / 6 hours)",
    )
    args = parser.parse_args()

    daemon = ExergyDaemon(check_interval=args.interval)
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        daemon.stop()
    except Exception as e:
        logging.critical("Fatal Crash: %s", e)
        daemon.stop()
