"""CORTEX Guard Daemon — Core.

Invisible background process that watches filesystem mutations,
classifies actions, routes through the guard pipeline, emits verdicts,
and persists the audit trail to the hash-chain ledger.

Architecture::

    FileSystem Watcher (watchfiles)
           ↓
    ActionClassifier (O(1) pattern match)
           ↓
    Passthrough Filter (reads → bypass)
           ↓
    AgenticPolicyEngine.evaluate_action()
           ↓
    Verdict → {PASS, WARN, BLOCK}
           ↓
    VerdictEmitter (terminal + log + ledger)

Usage::

    daemon = GuardDaemon(watch_path=".")
    await daemon.run()  # blocks until SIGINT/SIGTERM

Or via CLI::

    cortex guard start   # background
    cortex guard stop    # graceful shutdown
    cortex guard status  # introspect
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

from cortex.daemon.action_classifier import (
    ActionClassifier,
    ClassifiedAction,
    GuardLevel,
)
from cortex.daemon.verdict_emitter import (
    _DEFAULT_PID,
    GuardVerdict,
    VerdictEmitter,
)
from cortex.guards.policy_engine import AgenticPolicyEngine
from cortex.guards.verdicts import PolicyVerdict, VerdictReport

logger = logging.getLogger("cortex.daemon.guard")

# Debounce window: ignore rapid re-fires of the same file
_DEBOUNCE_MS = 300


class GuardDaemon:
    """The Sovereign Guard Daemon.

    Watches a directory for filesystem mutations, classifies each event,
    routes through the policy engine, and emits verdicts. Designed for
    zero-friction background operation.

    Args:
        watch_path: Directory to watch (default: cwd).
        policy_path: Path to cortex.policy.yaml.
        quiet: Suppress PASS verdicts in terminal.
        pid_file: Path to write daemon PID.
    """

    def __init__(
        self,
        watch_path: str = ".",
        policy_path: str = "cortex.policy.yaml",
        *,
        quiet: bool = True,
        pid_file: Path = _DEFAULT_PID,
        ledger_db: str | None = None,
    ) -> None:
        self._watch_path = Path(watch_path).resolve()
        self._policy_path = policy_path
        self._quiet = quiet
        self._pid_file = pid_file
        self._ledger_db = ledger_db
        self._running = False
        self._start_time: float = 0.0

        # Components (lazy init)
        self._classifier: ActionClassifier | None = None
        self._policy: AgenticPolicyEngine | None = None
        self._emitter: VerdictEmitter | None = None
        self._ledger: Any = None
        self._rollback_spine: Any = None

        # Debounce state
        self._last_events: dict[str, float] = {}

    def _init_components(self) -> None:
        """Initialize all daemon components."""
        # Classifier
        classifier_kwargs: dict[str, Any] = {}
        if self._policy and self._policy.policy:
            gateway = self._policy.policy.gateway
            if "daemon" in gateway:
                daemon_cfg = gateway["daemon"]
                if "ignore_patterns" in daemon_cfg:
                    classifier_kwargs["ignore_patterns"] = daemon_cfg["ignore_patterns"]
                if "passthrough_commands" in daemon_cfg:
                    classifier_kwargs["passthrough_commands"] = daemon_cfg["passthrough_commands"]
        self._classifier = ActionClassifier(**classifier_kwargs)

        # Emitter
        self._emitter = VerdictEmitter(
            terminal=True,
            quiet=self._quiet,
        )

        # Ledger (optional)
        if self._ledger_db:
            try:
                import sqlite3

                from cortex.ledger.ledger_core import SovereignLedger

                conn = sqlite3.connect(self._ledger_db)
                self._ledger = SovereignLedger(conn)
                logger.info("Ledger connected: %s", self._ledger_db)
            except Exception:
                logger.warning("Ledger unavailable, verdicts will not be persisted")
                self._ledger = None

        # Rollback Spine (always available, optionally with DB)
        try:
            from cortex.daemon.rollback_spine import RollbackSpine

            self._rollback_spine = RollbackSpine(db_path=self._ledger_db)
            logger.info("RollbackSpine initialized with DB: %s", self._ledger_db)
        except Exception:
            logger.warning("Failed to initialize RollbackSpine")
            self._rollback_spine = None

    def _load_policy(self) -> None:
        """Load policy engine from YAML."""
        try:
            self._policy = AgenticPolicyEngine(self._policy_path)
            logger.info("Policy loaded: %s", self._policy_path)
        except FileNotFoundError:
            logger.warning(
                "No policy file at %s — using permissive defaults",
                self._policy_path,
            )
            self._policy = None

    def _write_pid(self) -> None:
        """Write current PID to file for daemon management."""
        self._pid_file.parent.mkdir(parents=True, exist_ok=True)
        self._pid_file.write_text(str(os.getpid()), encoding="utf-8")
        logger.info("PID %d written to %s", os.getpid(), self._pid_file)

    def _cleanup_pid(self) -> None:
        """Remove PID file on shutdown."""
        try:
            if self._pid_file.exists():
                self._pid_file.unlink()
        except OSError:
            pass

    def _is_debounced(self, path: str) -> bool:
        """Check if this path was recently processed (debounce)."""
        now = time.monotonic() * 1000  # ms
        last = self._last_events.get(path, 0)
        if now - last < _DEBOUNCE_MS:
            return True
        self._last_events[path] = now
        return False

    def _evaluate(self, action: ClassifiedAction) -> GuardVerdict:
        """Route a classified action through the policy engine.

        Returns:
            GuardVerdict with the combined classification + policy result.
        """
        # Passthrough actions skip policy evaluation entirely
        if action.guard_level == GuardLevel.PASSTHROUGH:
            report = VerdictReport(verdict=PolicyVerdict.CORTEX_PASS)
            return GuardVerdict(action=action, report=report)

        # P0 Critical: always BLOCK (secret access, destructive commands)
        if action.guard_level == GuardLevel.P0_CRITICAL:
            report = VerdictReport(
                verdict=PolicyVerdict.CORTEX_BLOCK,
                rule_id=f"GUARD-{action.action_type.value.upper()}",
                description=action.detail,
                severity="CRITICAL",
            )
            return GuardVerdict(action=action, report=report)

        # P1/P2: Route through policy engine if available
        if self._policy:
            report = self._policy.evaluate_action(
                action_type=action.action_type.value,
                payload=f"{action.path} {action.detail}",
            )
            return GuardVerdict(action=action, report=report)

        # No policy engine: default to PASS with advisory
        if action.guard_level == GuardLevel.P1_HIGH:
            report = VerdictReport(
                verdict=PolicyVerdict.CORTEX_WARN,
                rule_id=f"GUARD-{action.action_type.value.upper()}",
                description=action.detail,
                severity="HIGH",
            )
            return GuardVerdict(action=action, report=report)

        report = VerdictReport(verdict=PolicyVerdict.CORTEX_PASS)
        return GuardVerdict(action=action, report=report)

    def _persist_verdict(self, verdict: GuardVerdict) -> None:
        """Persist verdict to ledger audit trail."""
        if not self._ledger or verdict.is_pass:
            return

        try:
            # Check if there is an active running asyncio event loop
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # Running in async context: schedule the async call
                    loop.create_task(self._persist_verdict_async(verdict))
                    return
            except RuntimeError:
                pass

            # Running in sync context (e.g. sync tests): run synchronously
            coro = self._ledger.append_verdict(
                verdict=verdict.report.verdict.value,
                reason=verdict.report.description or verdict.action.detail,
                target_path=verdict.action.path,
                action_type=verdict.action.action_type.value,
                tenant_id="default",
            )
            asyncio.run(coro)
        except Exception:
            logger.debug("Failed to persist verdict to ledger", exc_info=True)

    async def _persist_verdict_async(self, verdict: GuardVerdict) -> None:
        """Helper to await append_verdict asynchronously."""
        try:
            await self._ledger.append_verdict(
                verdict=verdict.report.verdict.value,
                reason=verdict.report.description or verdict.action.detail,
                target_path=verdict.action.path,
                action_type=verdict.action.action_type.value,
                tenant_id="default",
            )
        except Exception:
            logger.debug("Failed to persist verdict to ledger asynchronously", exc_info=True)

    def process_file_event(self, path: str) -> GuardVerdict | None:
        """Process a single filesystem event.

        Returns:
            GuardVerdict or None if debounced/ignored.
        """
        if not self._classifier or not self._emitter:
            return None

        if self._is_debounced(path):
            return None

        action = self._classifier.classify_file_event(path)
        verdict = self._evaluate(action)
        self._emitter.emit(verdict)
        self._persist_verdict(verdict)

        # Trigger snapshot if rules in cortex.policy.yaml dictate and rollback is enabled
        if verdict.report and verdict.report.rule_id:
            if self._policy and self._policy.policy:
                rollback_cfg = self._policy.policy.rollback
                if rollback_cfg.get("enabled", False):
                    snapshot_on = rollback_cfg.get("snapshot_on", [])
                    if verdict.report.rule_id in snapshot_on:
                        action_type = verdict.action.action_type.value
                        if verdict.report.rule_id == "migration_gate":
                            action_type = "migration"
                        reason = (
                            f"Rule matched: {verdict.report.rule_id} ({verdict.report.description})"
                        )
                        if self._rollback_spine:
                            try:
                                self._rollback_spine.create_snapshot(action_type, reason)
                            except Exception:
                                logger.debug("Failed to create rollback snapshot", exc_info=True)

        return verdict

    async def run(self) -> None:
        """Main daemon loop. Blocks until SIGINT/SIGTERM.

        Uses watchfiles for efficient filesystem monitoring
        (Rust-backed, inotify/kqueue/FSEvents under the hood).
        """
        try:
            from watchfiles import Change, awatch
        except ImportError:
            logger.error("watchfiles not installed. Run: pip install watchfiles")
            raise SystemExit(1)  # noqa: B904

        self._load_policy()
        self._init_components()
        self._write_pid()
        self._running = True
        self._start_time = time.time()

        # Install signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_shutdown)

        logger.info(
            "Guard Daemon started — watching %s (PID %d)",
            self._watch_path,
            os.getpid(),
        )

        # Startup banner
        if self._emitter and not self._quiet:
            try:
                from rich.console import Console
                from rich.panel import Panel

                console = Console(stderr=True)
                console.print(
                    Panel(
                        f"[bold #CCFF00]CORTEX Guard Daemon[/bold #CCFF00]\n"
                        f"[dim]Watching:[/dim] {self._watch_path}\n"
                        f"[dim]Policy:[/dim] {self._policy_path}\n"
                        f"[dim]PID:[/dim] {os.getpid()}\n"
                        f"[dim]Mode:[/dim] {'quiet' if self._quiet else 'verbose'}",
                        border_style="#2E5090",
                        title="[bold]🛡️ Sovereign Guard[/bold]",
                    )
                )
            except ImportError:
                print(  # noqa: T201
                    f"CORTEX Guard Daemon — watching {self._watch_path} (PID {os.getpid()})",
                    file=sys.stderr,
                )

        try:
            async for changes in awatch(
                self._watch_path,
                recursive=True,
                step=200,  # ms between checks
            ):
                if not self._running:
                    break

                for change_type, path in changes:
                    # Only process modifications and creations
                    if change_type in (Change.modified, Change.added):
                        self.process_file_event(path)

        except asyncio.CancelledError:
            pass
        finally:
            self._shutdown()

    def _signal_shutdown(self) -> None:
        """Signal handler for graceful shutdown."""
        logger.info("Shutdown signal received")
        self._running = False

    def _shutdown(self) -> None:
        """Clean shutdown sequence."""
        self._running = False
        self._cleanup_pid()

        if self._emitter:
            stats = self._emitter.stats
            logger.info(
                "Guard Daemon stopped — %d verdicts (pass=%d warn=%d block=%d passthrough=%d)",
                stats["total"],
                stats["pass"],
                stats["warn"],
                stats["block"],
                stats["passthrough"],
            )

        if self._ledger and hasattr(self._ledger, "db"):
            try:
                self._ledger.db.close()
            except Exception:  # noqa: S110
                pass

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def uptime_seconds(self) -> float:
        if not self._start_time:
            return 0.0
        return time.time() - self._start_time

    @classmethod
    def read_pid(cls, pid_file: Path = _DEFAULT_PID) -> int | None:
        """Read the daemon PID from file."""
        try:
            if pid_file.exists():
                return int(pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
        return None

    @classmethod
    def is_daemon_running(cls, pid_file: Path = _DEFAULT_PID) -> bool:
        """Check if the guard daemon is currently running."""
        pid = cls.read_pid(pid_file)
        if pid is None:
            return False
        try:
            os.kill(pid, 0)  # Signal 0 = check existence
            return True
        except OSError:
            return False

    @classmethod
    def stop_daemon(cls, pid_file: Path = _DEFAULT_PID) -> bool:
        """Send SIGTERM to running daemon.

        Returns:
            True if signal was sent successfully.
        """
        pid = cls.read_pid(pid_file)
        if pid is None:
            return False
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False
