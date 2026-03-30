"""
cortex/guards/taint.py
──────────────────────
Causal Taint Enforcement — v0.1.0 (Ω1, Ω3)
Enforces a deterministic audit trail for all agent-mediated mutations.
"""

import logging
import os
import re
import subprocess

logger = logging.getLogger("cortex.guards.taint")

class TaintGuard:
    """
    Ensures that every modification in a staged file contains a valid
    CORTEX Causal Taint signature.

    Pattern: # CORTEX-TAINT: <agent_id>:<hash>:<timestamp>
    """

    TAINT_PATTERN = r"CORTEX-TAINT: ([\w-]+):([\w]+):([\d.]+)"

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def get_staged_files(self) -> list[str]:
        """Returns a list of files staged for commit."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return [f for f in result.stdout.splitlines() if f]
        except subprocess.CalledProcessError:
            return []

    def verify_file_taint(self, file_path: str) -> tuple[bool, str]:
        """
        Checks if the staged changes in a file include a valid taint header.
        If the file is new or modified by an agent, it must have a taint.
        """
        full_path = os.path.join(self.repo_path, file_path)
        if not os.path.exists(full_path):
            return True, "File deleted (no taint needed)"

        # Only check .py, .md, .js files for now
        if not any(file_path.endswith(ext) for ext in [".py", ".md", ".js", ".sh"]):
            return True, "Ignored extension"

        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            # Look for the signature anywhere in the file (usually top or bottom)
            match = re.search(self.TAINT_PATTERN, content)
            if not match:
                return False, f"Missing CORTEX-TAINT header in {file_path}"

            agent_id, content_hash, timestamp = match.groups()
            logger.info("[TAINT] Verified: agent=%s, hash=%s, ts=%s", agent_id, content_hash, timestamp)
            return True, f"Verified taint for {agent_id}"

        except Exception as e:
            return False, f"Error reading {file_path}: {e}"

    def check_all_staged(self) -> bool:
        """Runs the verification on all staged files."""
        files = self.get_staged_files()
        if not files:
            return True

        failures = []
        for f in files:
            ok, msg = self.verify_file_taint(f)
            if not ok:
                failures.append(msg)

        if failures:
            print("\n" + "!" * 80)
            print("CORTEX TAINT VIOLATION (Ω1/Ω3)")
            for msg in failures:
                print(f" - {msg}")
            print("Action: Add '# CORTEX-TAINT: <agent-id>:<hash>:<timestamp>' to staged files.")
            print("!" * 80 + "\n")
            return False

        return True

if __name__ == "__main__":
    guard = TaintGuard()
    if not guard.check_all_staged():
        exit(1)
    exit(0)
