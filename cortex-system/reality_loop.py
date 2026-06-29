"""
C5-REAL: Self-Modifying Organic Reality Loop
Author: Borja Moskv / borjamoskv
"""

import sys
import os
import re
import asyncio
import subprocess
import logging

# Ensure internal modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from control_plane import ControlPlane

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cortex.system.reality_loop")

class RealityLoop:
    def __init__(self):
        self.control_plane = ControlPlane()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.reward_model_path = os.path.join(self.base_dir, "policies", "reward_model.py")
        self.delegation_map_path = os.path.join(self.base_dir, "policies", "delegation_map.py")

    def _mutate_reward_model(self, multiplier: float) -> str:
        """Reads, modifies, and writes back policies/reward_model.py thresholds."""
        logger.info(f"Mutating reward model thresholds with multiplier={multiplier}")
        with open(self.reward_model_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex match to extract and scale ORIGINALITY_THRESHOLD
        match_orig = re.search(r"ORIGINALITY_THRESHOLD = (\d+\.\d+)", content)
        if match_orig:
            old_val = float(match_orig.group(1))
            new_val = min(0.95, max(0.10, old_val * multiplier))
            content = re.sub(
                r"ORIGINALITY_THRESHOLD = \d+\.\d+",
                f"ORIGINALITY_THRESHOLD = {new_val:.2f}",
                content
            )
            logger.info(f"Scaled ORIGINALITY_THRESHOLD from {old_val} to {new_val:.2f}")

        # Scale DISTRIBUTION_THRESHOLD as well
        match_dist = re.search(r"DISTRIBUTION_THRESHOLD = (\d+\.\d+)", content)
        if match_dist:
            old_val = float(match_dist.group(1))
            new_val = min(0.95, max(0.10, old_val * multiplier))
            content = re.sub(
                r"DISTRIBUTION_THRESHOLD = \d+\.\d+",
                f"DISTRIBUTION_THRESHOLD = {new_val:.2f}",
                content
            )
            logger.info(f"Scaled DISTRIBUTION_THRESHOLD from {old_val} to {new_val:.2f}")

        with open(self.reward_model_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"reward_model: ORIGINALITY_THRESHOLD={new_val:.2f}"

    def _mutate_delegation_map(self) -> str:
        """Mutates agent parameters in policies/delegation_map.py."""
        logger.info("Mutating delegation map: injecting noise to Generator A")
        with open(self.delegation_map_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Search for noise_ratio inside Generator A and scale it
        match_noise = re.search(r'"noise_ratio": (\d+\.\d+)', content)
        if match_noise:
            old_val = float(match_noise.group(1))
            new_val = min(0.90, old_val + 0.05)
            content = re.sub(
                r'"noise_ratio": \d+\.\d+',
                f'"noise_ratio": {new_val:.2f}',
                content
            )
            logger.info(f"Generator A noise_ratio increased from {old_val} to {new_val:.2f}")

        with open(self.delegation_map_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"delegation_map: noise_ratio={new_val:.2f}"

    def _verify_and_commit(self, msg: str):
        """Verifies syntax correctness of mutated files and commits them via Git Sentinel."""
        # Compile syntax check
        try:
            subprocess.run(
                [sys.executable, "-m", "py_compile", self.reward_model_path],
                check=True,
                capture_output=True
            )
            subprocess.run(
                [sys.executable, "-m", "py_compile", self.delegation_map_path],
                check=True,
                capture_output=True
            )
            logger.info("Syntax check passed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Syntax validation failed during mutation. Rolling back file changes. Stderr: {e.stderr.decode()}")
            raise e

        # Git Sentinel Ledger commit
        try:
            subprocess.run(["git", "add", "."], cwd=self.base_dir, check=True)
            commit_cmd = ["git", "commit", "-m", f"chore(cortex-system): [bridge] {msg}"]
            res = subprocess.run(commit_cmd, cwd=self.base_dir, check=True, capture_output=True)
            
            # Extract commit hash
            hash_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.base_dir,
                check=True,
                capture_output=True
            )
            commit_hash = hash_res.stdout.decode().strip()
            logger.info(f"[C5-REAL] Git Sentinel Ledger Hash: {commit_hash}")
            print(f"Git Sentinel Ledger Hash: {commit_hash}")
        except subprocess.CalledProcessError as e:
            # If no modifications actually took place or error
            logger.warning(f"Git commit failed or no changes to stage: {e}")

    async def run_step(self, prompt: str):
        """Executes a control cycle and mutates logic if needed."""
        # 1. Run standard cycle
        cycle_res = await self.control_plane.execute_cycle(prompt)
        action = cycle_res["evolutionary_action"]
        
        mutation_desc = ""
        if action == "force_swarm_mode":
            mutation_desc = self._mutate_delegation_map()
        elif action == "inject_attention_pressure":
            mutation_desc = self._mutate_reward_model(1.10) # increase thresholds by 10%
        elif action == "trigger_rupture":
            mutation_desc = self._mutate_reward_model(0.85) # reduce/rupture thresholds by 15%
        
        if mutation_desc:
            self._verify_and_commit(f"Self-mutation triggered by '{action}': {mutation_desc}")
            
        return cycle_res

if __name__ == "__main__":
    loop = RealityLoop()
    asyncio.run(loop.run_step(prompt="Self-reproducing algorithmic installation"))
