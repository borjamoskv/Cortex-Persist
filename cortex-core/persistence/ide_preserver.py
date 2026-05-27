
import os
import time
import hashlib
import asyncio
import subprocess

from .base import ledger_entropy_event, logger
from .ledger import LedgerManager

try:
    import cortex_rs  # noqa: F401
except ImportError:
    pass

class IdeStatePreserver:
    """Guardian para proteger el entorno IDE/Agent contra fallas estructurales."""

    def __init__(self, ledger: LedgerManager):
        self.ledger = ledger
        self.backup_dir = os.path.expanduser("~/cortex_backups")
        self.target_dir = os.path.expanduser("~/.gemini/antigravity")
        self._daemon_task = None

    async def _execute_snapshot_async(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        try:
            backups = sorted([os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.startswith("antigravity_state_") and f.endswith(".tar.gz")], key=os.path.getmtime)
            while len(backups) >= 2:
                oldest = backups.pop(0)
                os.remove(oldest)
        except Exception as e:
            logger.warning(f'Silenced exception: {e}')

        timestamp = int(time.monotonic())
        archive_path = os.path.join(self.backup_dir, f"antigravity_state_{timestamp}.tar.gz")

        try:
            # C5-REAL snapshot using non-blocking async subprocess (Zero OS-Thread Friction)
            proc = await asyncio.create_subprocess_exec(
                "/usr/bin/tar", "-czf", archive_path, "--exclude=brain", self.target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                hasher = hashlib.sha256()
                with open(archive_path, "rb") as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                backup_hash = hasher.hexdigest()

                # Register in L3 Ledger
                self.ledger.append(
                    action="IDE_STATE_SNAPSHOT", vector_id=f"hash:{backup_hash[:16]}", yield_amount=0.0
                )
                logger.info("IDE State Snapshot secured: %s", archive_path)
            else:
                logger.error("Failed to snapshot IDE state: %s", stderr.decode())
        except Exception as e:
            logger.error("Failed to snapshot IDE state: %s", e)

    def _execute_snapshot_sync(self):
        """Fallback for environments without a running event loop."""
        os.makedirs(self.backup_dir, exist_ok=True)
        try:
            backups = sorted([os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.startswith("antigravity_state_") and f.endswith(".tar.gz")], key=os.path.getmtime)
            while len(backups) >= 2:
                oldest = backups.pop(0)
                os.remove(oldest)
        except Exception as e:
            logger.warning(f'Silenced exception: {e}')

        timestamp = int(time.monotonic())
        archive_path = os.path.join(self.backup_dir, f"antigravity_state_{timestamp}.tar.gz")
        try:
            subprocess.run(["/usr/bin/tar", "-czf", archive_path, "--exclude=brain", self.target_dir], check=True, capture_output=True)
            logger.info("IDE State Snapshot secured (Sync Fallback): %s", archive_path)
        except Exception as e:
            logger.error("Failed to snapshot IDE state sync: %s", e)

    async def _snapshot_loop(self):
        """Entropy-driven snapshots. Triggered precisely by Ledger cryptographic volume."""
        loop = asyncio.get_running_loop()
        while True:
            await loop.run_in_executor(None, ledger_entropy_event.wait)
            ledger_entropy_event.clear()
            await self._execute_snapshot_async()

    def start_guardian(self):
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._snapshot_loop())
        except RuntimeError:
            logger.warning("IDE State Preserver loop could not be started: no running event loop.")
            # Fallback sync run once
            self._execute_snapshot_sync()


