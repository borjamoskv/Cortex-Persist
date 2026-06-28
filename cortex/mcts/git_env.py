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

from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile

logger = logging.getLogger("cortex.mcts.git_env")


class MCTSGitEnvironment:
    """Quantum Git Environment for the AlphaZero Autodidact."""

    def __init__(self, router: CortexLLMRouter, target_file: Path) -> None:
        self.router = router
        self.target_file = Path(target_file).absolute()
        if not self.target_file.exists():
            raise FileNotFoundError(f"Target file does not exist: {self.target_file}")

    async def get_current_branch(self) -> str:
        """Returns the name of the current branch."""
        proc = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()

    async def branch_out(self, base_branch: str, new_node_id: str) -> str:
        """Branches out the Git tree."""
        new_name = f"chronos/node-{new_node_id}"
        cmd = f"git checkout -b {shlex.quote(new_name)} {shlex.quote(base_branch)}"
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0:
            # Fallback for existing branch
            await asyncio.create_subprocess_shell(
                f"git checkout {shlex.quote(new_name)}"
            ).communicate()  # pyright: ignore[reportAttributeAccessIssue]
        return new_name

    async def mutate(self, prompt_instruction: str) -> bool:
        """Injects an LLM mutation into the target file."""
        original_code = self.target_file.read_text(encoding="utf-8")

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
            temperature=0.8,  # High temperature to force evolutionary divergence
            max_tokens=8192,
        )

        res = await self.router.execute_resilient(prompt)
        if res.is_err():
            logger.error("LLM mutation error: %s", res.error)  # pyright: ignore[reportAttributeAccessIssue]
            return False

        new_code = res.unwrap().strip()
        # Clean markdown if present
        if new_code.startswith("```"):
            lines = new_code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            new_code = "\n".join(lines).strip()

        self.target_file.write_text(new_code, encoding="utf-8")
        logger.info("🧬 [CHRONOS] Mutated file: %s", self.target_file.name)
        return True

    async def simulate(self) -> float:
        """Plays the multiverse: Runs pytest and calculates Yield and Exergy.

        Reward Function:
        1.0 if it passes clean tests,
        0.0 if it breaks system integrity.
        (Future: multiply by thermal efficiency/latency).
        """
        logger.info("🧪 [CHRONOS] Running integrity simulation (pytest)...")
        start_time = time.perf_counter()

        # We run the complete test suite or ruff rules to check syntax
        cmd_ruff = f"ruff check {shlex.quote(str(self.target_file))}"
        proc_ruff = await asyncio.create_subprocess_shell(
            cmd_ruff, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc_ruff.communicate()

        if proc_ruff.returncode != 0:
            logger.warning("💥 [CHRONOS] Mutation annihilated: Invalidates strict linter.")
            return 0.0

        cmd_test = "pytest tests/ -v -q --tb=no"
        proc_test = await asyncio.create_subprocess_shell(
            cmd_test, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc_test.communicate()

        duration = time.perf_counter() - start_time

        if proc_test.returncode == 0:
            logger.info(
                "💎 [CHRONOS] Thermodynamically viable mutation (Passed in %.2fs).", duration
            )
            # In the P0 version, it is binary
            return 1.0
        logger.warning("💥 [CHRONOS] Mutation annihilated: Fails assertion or causes regression.")
        return 0.0

    async def secure_checkout(self, branch: str) -> None:
        """Returns to a safe branch restoring any changes."""
        logger.debug("Restoring entropy: checkout to %s", branch)
        await asyncio.create_subprocess_shell("git reset --hard HEAD").communicate()  # pyright: ignore[reportAttributeAccessIssue]
        await asyncio.create_subprocess_shell("git clean -fd").communicate()  # pyright: ignore[reportAttributeAccessIssue]
        await asyncio.create_subprocess_shell(f"git checkout {shlex.quote(branch)}").communicate()  # pyright: ignore[reportAttributeAccessIssue]
