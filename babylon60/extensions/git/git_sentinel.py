# [C5-REAL] Exergy-Maximized
"""
Git Sentinel - C5-REAL Silent Auto-Commit for Zero-Prompt Daemon.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger("babylon60.git.sentinel")


class GitSentinel:
    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)

    async def silent_commit(self, file_path: str) -> None:
        """
        Executes a silent commit for the mutated file.
        Enforces AX-041: No Hidden Entropy.
        """
        if not self.repo_path.exists():
            return

        logger.info("Git Sentinel: Preparing silent commit for %s", file_path)

        try:
            # Enforce C5-REAL Structural Integrity Check (Ruff)
            logger.info("Git Sentinel: Verifying structural integrity via Ruff.")
            proc_check = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                file_path,
                cwd=str(self.repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_check, stderr_check = await proc_check.communicate()
            if proc_check.returncode != 0:
                logger.error(
                    "Git Sentinel: Structural Integrity Failed (C4-SIM detected). Aborting silent commit.\n%s",
                    stdout_check.decode(),
                )
                return

            # Stage the file
            proc_add = await asyncio.create_subprocess_exec(
                "git",
                "add",
                file_path,
                cwd=str(self.repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc_add.communicate()
            if proc_add.returncode != 0:
                logger.debug("Git Sentinel: File %s could not be added (maybe ignored).", file_path)
                return

            # Commit the file
            msg = f"[bridge] Auto-crystallize mutation: {Path(file_path).name}"
            proc_commit = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                msg,
                "--no-verify",
                cwd=str(self.repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc_commit.communicate()

            if proc_commit.returncode == 0:
                logger.info("Git Sentinel: Immutable commit generated for %s", file_path)
            else:
                logger.debug(
                    "Git Sentinel: Nothing to commit or commit failed. %s", stderr.decode()
                )

        except Exception as e:
            logger.error("Git Sentinel Byzantine Fault: %s", e)
