# [C5-REAL] Exergy-Maximized
"""
APEX-008: Contención Epistémica Autónoma (Ouroboros Immune).
Enforces R9: Prevents infinite commit loops by detecting recursive
auto-generated files (logs, temp dumps) and dynamically quarantining
them in .git/info/exclude.
"""

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger("cortex.engine.causal.ouroboros_immune")


class OuroborosImmuneSystem:
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root).resolve()
        self.exclude_file = self.repo_root / ".git" / "info" / "exclude"
        self.suspect_patterns = [
            re.compile(r".*\.log$"),
            re.compile(r".*scratch/.*"),
            re.compile(r".*\.tmp$"),
            re.compile(r".*cortex_meta.*"),
            re.compile(r".*audit_exports.*"),
        ]

    def _get_untracked_files(self) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return [f for f in result.stdout.split("\n") if f]
        except subprocess.CalledProcessError as e:
            logger.error(f"Git execution failed: {e}")
            return []

    def scan_and_quarantine(self) -> list[str]:
        if not self.exclude_file.exists():
            if not self.exclude_file.parent.exists():
                logger.warning("No .git directory found. Cannot apply Ouroboros Immune.")
                return []
            self.exclude_file.touch()

        untracked = self._get_untracked_files()
        quarantined = []

        with open(self.exclude_file) as f:
            existing_excludes = set(f.read().splitlines())

        new_excludes = []
        for file_path in untracked:
            for pattern in self.suspect_patterns:
                if pattern.match(file_path):
                    if file_path not in existing_excludes:
                        new_excludes.append(file_path)
                        quarantined.append(file_path)
                    break

        if new_excludes:
            with open(self.exclude_file, "a") as f:
                for ex in new_excludes:
                    f.write(f"\n{ex}")
            logger.info(f"Ouroboros Quarantine updated. Isolated {len(new_excludes)} vectors.")

        return quarantined
