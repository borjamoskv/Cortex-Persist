"""
Git Sentinel Daemon.

[C5-REAL] UltraThink Mitigation for V-016 (Git Hook Bypass).
Asynchronously monitors the git index and decapitates unanchored commits.
"""

import asyncio
import logging
import subprocess

import aiosqlite

from babylon60.audit.ledger import EnterpriseAuditLedger

logger = logging.getLogger("babylon60.guards.git_sentinel_daemon")


class GitSentinelDaemon:
    def __init__(self, db_path: str = "cortex.db", check_interval: float = 2.0):
        self.db_path = db_path
        self.check_interval = check_interval
        self._running = False
        self._task: asyncio.Task | None = None
        # Track the last seen hash to avoid verifying the same commit over and over.
        self._last_checked_hash = ""

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("[C5-REAL] Git Sentinel Daemon starting in Ouroboros Watchdog mode.")
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[C5-REAL] Git Sentinel Daemon stopped.")

    async def _watch_loop(self) -> None:
        # Give the DB time to initialize if we start concurrently
        await asyncio.sleep(1.0)

        while self._running:
            try:
                await self._check_latest_commit()
            except Exception as e:  # noqa: BLE001
                # Capturamos Exception genérica para aislar el Event Loop (LL-AC-02, LL-AC-03).
                logger.error("[GitSentinelDaemon] Loop error: %s", e)
            await asyncio.sleep(self.check_interval)

    async def _check_latest_commit(self) -> None:
        # Get latest commit
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H"], capture_output=True, text=True, check=True
            )
            latest_hash = result.stdout.strip()
        except subprocess.CalledProcessError:
            # Not a git repo or no commits yet
            return

        if not latest_hash or latest_hash == self._last_checked_hash:
            return

        # We have a new commit to check
        async with aiosqlite.connect(self.db_path) as conn:
            ledger = EnterpriseAuditLedger(conn)
            is_valid = await ledger.verify_git_commit(latest_hash)

            if not is_valid:
                logger.critical(
                    "[C5-REAL] UNAUTHORIZED COMMIT DETECTED (V-016 Bypass Attempt). Apoptosis initiated."
                )
                logger.critical("Target Hash: %s", latest_hash)

                # Decapitate the unanchored entropy
                try:
                    subprocess.run(
                        ["git", "reset", "--hard", "HEAD~1"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    logger.critical("[C5-REAL] Apoptosis Complete. Entropy reverted.")

                    # Log the breach explicitly
                    await ledger.log_action(
                        tenant_id="SYSTEM",
                        actor_role="GitSentinelDaemon",
                        actor_id="daemon_ouroboros",
                        action="APOPTOSIS_EXECUTION",
                        resource=f"reverted_hash:{latest_hash}",
                        status="BREACH_CONTAINED",
                    )
                except subprocess.CalledProcessError as reset_err:
                    logger.error(
                        "[C5-REAL] Failed to execute Apoptosis on %s: %s", latest_hash, reset_err
                    )
            else:
                self._last_checked_hash = latest_hash
