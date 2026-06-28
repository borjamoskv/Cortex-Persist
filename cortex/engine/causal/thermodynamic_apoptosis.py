"""
[C5-REAL] CORTEX APEX: Thermodynamic Apoptosis Engine.
Domain: Causal Convergence & Ouroboros Collapse.

Implements the 'Galaxy Brain' topology for Idea Convergence.
Divergent conceptual branches are evaluated empirically via A-EVAL-2026.
Branches with negative/inferior Net Improvement suffer Apoptosis (physical destruction).
The highest-exergy branch auto-integrates into the Master Trunk.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

import aiosqlite

from cortex.audit.ledger import EnterpriseAuditLedger

logger = logging.getLogger("cortex.engine.causal.apoptosis")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

class OuroborosCollapseEngine:
    def __init__(self, repo_path: Path, db_path: str = "cortex_ledger.db"):
        self.repo_path = repo_path
        self.db_path = db_path

    def _get_branch_exergy(self, branch_name: str) -> float:
        """
        Calculates Net Improvement (Exergy Delta) for a specific branch.
        Uses Git Sentinel empirical data.
        """
        try:
            # Count total commits in branch
            total_cmd = subprocess.run(
                ["git", "rev-list", "--count", branch_name], 
                cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            total_commits = int(total_cmd.stdout.strip() or 1)

            # Count reverts/fixes
            revert_cmd = subprocess.run(
                ["git", "log", "--oneline", "--grep=revert", "--grep=fix", "-i", branch_name], 
                cwd=self.repo_path, capture_output=True, text=True, check=True
            )
            revert_commits = len([line for line in revert_cmd.stdout.splitlines() if line])

            # Net Improvement
            return ((total_commits - revert_commits) / total_commits) * 100
        except Exception as e:
            logger.error(f"Failed to compute exergy for branch {branch_name}: {e}")
            return -float("inf")

    def _execute_apoptosis(self, branch_name: str) -> None:
        """Destroys a branch structurally."""
        try:
            logger.warning(f"[APOPTOSIS] Destroying sub-optimal branch: {branch_name}")
            subprocess.run(["git", "branch", "-D", branch_name], cwd=self.repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Apoptosis failed for {branch_name}: {e.stderr}")

    def _collapse_wave(self, winner_branch: str) -> bool:
        """Merges the highest-exergy branch into the current HEAD (main)."""
        try:
            logger.info(f"[COLLAPSE] Integrating structural invariant from: {winner_branch}")
            subprocess.run(["git", "merge", "--no-ff", "-m", f"chore(convergence): ouroboros collapse of {winner_branch}", winner_branch], 
                           cwd=self.repo_path, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Wave collapse failed for {winner_branch}. Git conflicts likely: {e.stderr}")
            # Rollback merge
            subprocess.run(["git", "merge", "--abort"], cwd=self.repo_path, capture_output=True)
            return False

    async def run_convergence(self, target_branches: list[str]) -> Optional[str]:
        """
        Evaluates a list of divergent branches, collapses the best one, and triggers
        apoptosis on the rest. Anchors cryptographic proof in the Ledger.
        """
        if not target_branches:
            logger.warning("No divergent branches provided for convergence.")
            return None

        evaluations: dict[str, float] = {}
        for branch in target_branches:
            evaluations[branch] = self._get_branch_exergy(branch)
            logger.info(f"Branch {branch} - Exergy Yield: {evaluations[branch]:.2f}%")

        # Find the max exergy
        winner = max(evaluations, key=evaluations.get)
        losers = [b for b in target_branches if b != winner]

        from cortex.database.core import connect_async_ctx
        async with connect_async_ctx(self.db_path) as conn:
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()

            # 1. Apoptosis
            for loser in losers:
                self._execute_apoptosis(loser)
                await ledger.log_action(
                    tenant_id="global",
                    actor_role="system",
                    actor_id="ouroboros_collapse",
                    action="THERMODYNAMIC_APOPTOSIS",
                    resource=loser,
                    status=f"Yield:{evaluations[loser]:.2f}%"
                )

            # 2. Wave Collapse (Merge)
            success = self._collapse_wave(winner)
            
            if success:
                # Clean up the winner branch post-merge
                self._execute_apoptosis(winner)
                
                await ledger.log_action(
                    tenant_id="global",
                    actor_role="system",
                    actor_id="ouroboros_collapse",
                    action="WAVE_COLLAPSED_INTEGRATION",
                    resource=winner,
                    status=f"Yield:{evaluations[winner]:.2f}%"
                )
                logger.info(f"[C5-REAL] Convergence achieved. {winner} rules the domain.")
                return winner
            else:
                await ledger.log_action(
                    tenant_id="global",
                    actor_role="system",
                    actor_id="ouroboros_collapse",
                    action="COLLAPSE_FAILED",
                    resource=winner,
                    status="Merge Conflict"
                )
                return None

if __name__ == "__main__":
    # Test stub for CLI exposure
    import sys
    if len(sys.argv) > 1:
        branches = sys.argv[1:]
        engine = OuroborosCollapseEngine(Path("."))
        asyncio.run(engine.run_convergence(branches))
    else:
        import logging
        logging.getLogger(__name__).warning("Usage: python thermodynamic_apoptosis.py <branch1> <branch2> ...")
