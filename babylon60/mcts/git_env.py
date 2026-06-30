# [C5-REAL] Exergy-Maximized
"""MCTS Git Simulation Environment (Chronos).

Provides the deterministic interface to branch out the CORTEX multiverse,
inject mutations, and simulate thermodynamic exergy.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
import time
from pathlib import Path

from babylon60.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile

logger = logging.getLogger("cortex.mcts.git_env")


class MCTSGitEnvironment:
    """Quantum Git Environment for the AlphaZero Autodidact (Parallelized)."""

    def __init__(self, router: CortexLLMRouter, target_file: Path) -> None:
        self.router = router
        self.repo_root = Path(target_file).parent
        while self.repo_root != self.repo_root.parent and not (self.repo_root / ".git").exists():
            self.repo_root = self.repo_root.parent
        self.target_file_relative = Path(target_file).relative_to(self.repo_root)
        self.worktrees_dir = self.repo_root.parent / "cortex_mcts_worktrees"
        self.worktrees_dir.mkdir(exist_ok=True)

    async def get_current_branch(self) -> str:
        """Returns the name of the current branch in the main repo."""
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--abbrev-ref", "HEAD",
            stdout=asyncio.subprocess.PIPE, cwd=str(self.repo_root)
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()

    def _get_worktree_path(self, node_id: str) -> Path:
        return self.worktrees_dir / f"node-{node_id}"

    async def branch_out(self, base_branch: str, new_node_id: str) -> str:
        """Branches out the Git tree into an isolated worktree."""
        new_name = f"chronos/node-{new_node_id}"
        wt_path = self._get_worktree_path(new_node_id)
        
        # Create branch in main repo first
        proc1 = await asyncio.create_subprocess_shell(
            f"git branch {shlex.quote(new_name)} {shlex.quote(base_branch)}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(self.repo_root)
        )
        await proc1.communicate()
        
        # Add worktree linked to that branch
        proc2 = await asyncio.create_subprocess_shell(
            f"git worktree add {shlex.quote(str(wt_path))} {shlex.quote(new_name)}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(self.repo_root)
        )
        await proc2.communicate()
        return new_name

    async def mutate(self, node_id: str, prompt_instruction: str) -> bool:
        """Injects an LLM mutation into the target file inside the worktree."""
        wt_path = self._get_worktree_path(node_id)
        wt_target = wt_path / self.target_file_relative
        
        if not wt_target.exists():
            logger.error("Worktree target file does not exist: %s", wt_target)
            return False

        original_code = wt_target.read_text(encoding="utf-8")

        prompt = CortexPrompt(
            system_instruction=(
                "You are CORTEX Chronos, the Quantum Software Architect. "
                "Mutate the following Python file strictly according to the task. "
                "Return ONLY the raw updated code. No markdown formatting if possible."
            ),
            working_memory=[
                {
                    "role": "user",
                    "content": f"Task: {prompt_instruction}\n\nCode:\n```python\n{original_code}\n```",
                }
            ],
            intent=IntentProfile.CODE,
            temperature=0.8,
            max_tokens=8192,
        )

        res = await self.router.execute_resilient(prompt)
        if res.is_err():
            logger.error("LLM mutation error: %s", res.error)  # pyright: ignore[reportAttributeAccessIssue]
            return False

        new_code = res.unwrap().strip()
        if new_code.startswith("```"):
            lines = new_code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            new_code = "\n".join(lines).strip()

        wt_target.write_text(new_code, encoding="utf-8")
        logger.info("🧬 [CHRONOS] Mutated worktree file: %s", wt_target.name)
        return True

    async def simulate(self, node_id: str) -> float:
        """Plays the multiverse inside the isolated worktree."""
        wt_path = self._get_worktree_path(node_id)
        wt_target = wt_path / self.target_file_relative
        
        logger.info("🧪 [CHRONOS] Running integrity simulation (pytest) on %s...", node_id)
        start_time = time.perf_counter()

        cmd_ruff = f"ruff check {shlex.quote(str(wt_target))}"
        proc_ruff = await asyncio.create_subprocess_shell(
            cmd_ruff, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(wt_path)
        )
        await proc_ruff.communicate()

        if proc_ruff.returncode != 0:
            logger.warning("💥 [CHRONOS] Mutation annihilated: Invalidates strict linter.")
            return 0.0

        cmd_test = "pytest tests/ -v -q --tb=no"
        proc_test = await asyncio.create_subprocess_shell(
            cmd_test, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(wt_path)
        )
        await proc_test.communicate()

        duration = time.perf_counter() - start_time

        if proc_test.returncode == 0:
            logger.info("💎 [CHRONOS] Thermodynamically viable mutation (Passed in %.2fs).", duration)
            return 1.0
            
        logger.warning("💥 [CHRONOS] Mutation annihilated: Fails assertion or causes regression.")
        return 0.0

    async def secure_checkout(self, node_id: str) -> None:
        """Removes the isolated worktree and cleans up the branch if needed."""
        wt_path = self._get_worktree_path(node_id)
        branch_name = f"chronos/node-{node_id}"
        logger.debug("Removing worktree: %s and branch: %s", wt_path, branch_name)
        
        # 1. Remove worktree
        p1 = await asyncio.create_subprocess_shell(
            f"git worktree remove --force {shlex.quote(str(wt_path))}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(self.repo_root)
        )
        await p1.communicate()
        
        # 2. Delete the temporary branch
        p2 = await asyncio.create_subprocess_shell(
            f"git branch -D {shlex.quote(branch_name)}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(self.repo_root)
        )
        await p2.communicate()

    async def prune_orphans(self) -> dict[str, int]:
        """[LEA-OMEGA] Garbage Collector for orphaned MCTS worktrees and branches.
        
        Returns:
            dict: Metrics of pruning (worktrees_removed, branches_removed).
        """
        metrics = {"worktrees_removed": 0, "branches_removed": 0}
        
        # 1. Prune orphaned worktrees
        if self.worktrees_dir.exists() and self.worktrees_dir.is_dir():
            for wt_path in self.worktrees_dir.iterdir():
                if wt_path.is_dir() and wt_path.name.startswith("node-"):
                    logger.info("🗑️  [CHRONOS GC] Pruning orphaned worktree: %s", wt_path.name)
                    # Try git worktree remove
                    p1 = await asyncio.create_subprocess_shell(
                        f"git worktree remove --force {shlex.quote(str(wt_path))}",
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                        cwd=str(self.repo_root)
                    )
                    await p1.communicate()
                    
                    # If it's still there (e.g. untracked files or corrupted), rm -rf it
                    if wt_path.exists():
                        import shutil
                        shutil.rmtree(wt_path, ignore_errors=True)
                    metrics["worktrees_removed"] += 1
        
        # 2. Prune orphaned branches
        p_list = await asyncio.create_subprocess_shell(
            "git branch --list 'chronos/node-*'",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(self.repo_root)
        )
        stdout, _ = await p_list.communicate()
        branches = [b.strip().lstrip("* ") for b in stdout.decode().split("\n") if b.strip()]
        
        for branch in branches:
            logger.info("🗑️  [CHRONOS GC] Pruning orphaned branch: %s", branch)
            p_del = await asyncio.create_subprocess_shell(
                f"git branch -D {shlex.quote(branch)}",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=str(self.repo_root)
            )
            await p_del.communicate()
            metrics["branches_removed"] += 1
            
        return metrics
