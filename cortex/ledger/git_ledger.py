"""CORTEX-Persist // Git Sovereign Ledger v1.0.0

AX-041: Git DAG is the immutable source of truth.
All state mutations are serialized to canonical JSON,
cryptographically signed with SHA-256 CORTEX-TAINT,
and committed via non-blocking threadpool operations.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from cortex.guards.admission import byzantine_frontier_guard

logger = logging.getLogger("cortex.ledger.git")
logger.setLevel(logging.INFO)


@dataclass(frozen=True, slots=True)
class TaintedState:
    """Immutable record of a ledger mutation with its cryptographic taint."""

    taint: str
    file_path: str
    commit_sha: str
    payload_keys: tuple[str, ...] = field(default_factory=tuple)


class GitSovereignLedger:
    """Async Git-DAG ledger enforcing deterministic write-path.

    Constructor accepts ``workspace_root`` (Path | str) pointing at a
    directory that **must** be inside an initialized git repository.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self._validate_git_repo()

    # ── Public API ────────────────────────────────────────────────

    @byzantine_frontier_guard(strict=False)
    async def commit_state(
        self,
        state_mutation: Dict[str, Any],
        file_name: str = "state.json",
        commit_message: str = "CORTEX: state mutation",
    ) -> TaintedState:
        """Persist *state_mutation* into the Git DAG.

        1. Canonical JSON serialisation.
        2. SHA-256 CORTEX-TAINT computation.
        3. Async file write + ``git add`` + ``git commit``.
        """
        canonical = self._canonical_json(state_mutation)
        taint = self._compute_taint(canonical)

        target = self.workspace_root / file_name
        target.parent.mkdir(parents=True, exist_ok=True)

        # Non-blocking I/O via threadpool
        await asyncio.to_thread(target.write_text, canonical, "utf-8")
        commit_sha = await asyncio.to_thread(
            self._git_commit, str(target), f"{commit_message} [TAINT:{taint[:12]}]"
        )

        ts = TaintedState(
            taint=taint,
            file_path=str(target.relative_to(self.workspace_root)),
            commit_sha=commit_sha,
            payload_keys=tuple(state_mutation.keys()),
        )
        logger.info("Ledger commit: %s  taint=%s", commit_sha[:8], taint[:12])
        return ts

    async def record_mutation(
        self,
        state_mutation: Dict[str, Any],
        file_name: str = "state.json",
        commit_message: str = "CORTEX: mutation",
    ) -> str:
        """Convenience wrapper returning just the taint hash string.

        Used by ``CrystallizerJIT`` and other downstream engines.
        """
        ts = await self.commit_state(
            state_mutation=state_mutation,
            file_name=file_name,
            commit_message=commit_message,
        )
        return ts.taint

    # ── Internals ─────────────────────────────────────────────────

    @staticmethod
    def _canonical_json(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _compute_taint(canonical: str) -> str:
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _git_commit(self, file_path: str, message: str) -> str:
        """Blocking git add + commit.  Runs inside ``asyncio.to_thread``."""
        cwd = str(self.workspace_root)
        subprocess.run(["git", "add", file_path], cwd=cwd, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", message, "--allow-empty"],
            cwd=cwd,
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _validate_git_repo(self) -> None:
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.workspace_root),
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise RuntimeError(
                f"Workspace {self.workspace_root} is not inside a git repository"
            ) from exc
