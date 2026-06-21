# [C5-REAL] Exergy-Maximized
"""
MCTS Planner Module.
Implements integer-based structural trajectory planning.
"""

import logging
import struct
import hashlib

logger = logging.getLogger(__name__)

class MCTSPlanner:
    """
    Simulates forward trajectories via deterministic tree search.
    """

    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self.actions = [b"noop", b"flush_cache", b"restart_node", b"throttle_cpu"]

    def _simulate_transition(self, cpu: int, ram: int, latency: int, action: bytes) -> tuple[int, int, int]:
        """Deterministic state transition under BABYLON-60 integer rules."""
        if action == b"flush_cache":
            return min(10000, cpu + 500), max(1000, ram - 2000), max(5, latency - 15)
        elif action == b"restart_node":
            return min(10000, cpu + 1500), 2000, max(5, latency + 100)
        elif action == b"throttle_cpu":
            return max(1000, cpu - 2000), ram, latency + 15
        else: # noop
            return cpu, min(10000, ram + 100), latency

    def _evaluate_state(self, cpu: int, ram: int, latency: int) -> int:
        """Returns exergy value of the state (0-10000)."""
        cpu_penalty = cpu if cpu > 8000 else 0
        ram_penalty = ram if ram > 8000 else 0
        latency_penalty = latency * 10
        score = 10000 - (cpu_penalty + ram_penalty + latency_penalty) // 2
        return max(0, score)

    def _search_best_path(self, cpu: int, ram: int, latency: int, depth: int) -> tuple[list[bytes], int]:
        """Recursively searches all paths to find the optimal exergy trajectory."""
        if depth <= 0:
            return [], self._evaluate_state(cpu, ram, latency)

        best_score = -1
        best_path = []

        for action in self.actions:
            next_cpu, next_ram, next_latency = self._simulate_transition(cpu, ram, latency, action)
            sub_path, sub_score = self._search_best_path(next_cpu, next_ram, next_latency, depth - 1)
            
            # Path score is immediate evaluation + future score
            path_score = self._evaluate_state(next_cpu, next_ram, next_latency) + sub_score
            
            if path_score > best_score:
                best_score = path_score
                best_path = [action] + sub_path

        return best_path, best_score

    async def synthesize_plan(self, diagnosis: dict) -> dict:
        """
        Determines the single best action sequence.
        """
        # Default starting parameters
        cpu = diagnosis.get("cpu_pct_scaled", 5000)
        ram = diagnosis.get("ram_pct_scaled", 5000)
        latency = diagnosis.get("latency_ms", 45)

        logger.info(f"[C5-REAL] Synthesizing plan from CPU={cpu}, RAM={ram}, Latency={latency}")
        best_path, best_score = self._search_best_path(cpu, ram, latency, 1)

        # Scale expected exergy to Base-60 units (multiplied by 3600)
        expected_exergy = (best_score * 3600) // 10000

        return {
            "steps": best_path,
            "expected_exergy_units": expected_exergy
        }

    async def run_dream_simulation(self, diagnosis: dict) -> dict:
        """
        Evaluates offline state mutations across full depth.
        """
        cpu = diagnosis.get("cpu_pct_scaled", 5000)
        ram = diagnosis.get("ram_pct_scaled", 5000)
        latency = diagnosis.get("latency_ms", 45)

        logger.info(f"[C5-REAL] Running Dream MCTS Rollouts (Depth {self.max_depth})")
        best_path, best_score = self._search_best_path(cpu, ram, latency, self.max_depth)

        # Hash trajectory deterministically using SHA-256 and pack as u32
        sha = hashlib.sha256()
        for step in best_path:
            sha.update(step)
        traj_hash = sha.digest()[:4]

        expected_exergy = (best_score * 3600) // 10000

        return {
            "steps": best_path,
            "expected_exergy_units": expected_exergy,
            "trajectory_hash": traj_hash
        }
