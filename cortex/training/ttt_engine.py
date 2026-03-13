"""
CORTEX V7 — Test-Time Training (TTT) Engine.
The Event Horizon of Autonomous Evolution.

This engine runs during the Nocturnal Cycle (Conscious Recurrence).
It ingests trajectories from the day, filters them through the Reward Engine,
and executes local LoRA fine-tuning (via MLX) on trajectories with high
Aesthetic/Entropic rewards.

Axiom 10: Recursive Auto-Evolution. The model literally rewrites its own weights.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from cortex.training.collector import Trajectory, TrajectoryCollector
from cortex.training.reward_engine import RewardEngine

logger = logging.getLogger("cortex.training.ttt")


class TTTEngine:
    """
    Test-Time Training Orchestrator.
    Filters high-reward trajectories and triggers local MLX fine-tuning.
    """

    def __init__(self, episodic_memory: Any, triad: Any = None):
        self.collector = TrajectoryCollector(episodic_memory, triad)
        self.rewarder = RewardEngine(use_tests=True, triad=triad)

        self.dataset_dir = Path.home() / ".cortex" / "training" / "datasets"
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

        # We target the Qwen2.5 base model used by CORTEX
        self.base_model = os.getenv(
            "CORTEX_BASE_MODEL_PATH", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        )
        self.adapter_path = Path.home() / ".cortex" / "training" / "adapters"

    async def run_nocturnal_consolidation(self, session_ids: list[str]) -> dict[str, Any]:
        """
        The sleep cycle integration.
        1. Collects trajectories for the given sessions.
        2. Calculates RLHF/Sovereign rewards.
        3. Formats the 'Golden' trajectories (> 0.5 reward).
        4. Triggers MLX LoRA training if dataset size is sufficient.
        """
        logger.info("🌙 Initiating TTT Consolidation for %d sessions...", len(session_ids))

        golden_trajectories: list[Trajectory] = []
        total_reward = 0.0

        for sid in session_ids:
            try:
                traj = await self.collector.collect_session_trajectory(sid)
                if not traj:
                    continue

                reward = await self.rewarder.calculate_reward(traj)

                # Axiom Ω4: Aesthetic Integrity - Only learn from excellence
                if reward > 0.4:
                    traj.reward = reward
                    golden_trajectories.append(traj)
                    total_reward += reward
                    logger.debug("✨ Golden Trajectory found: %s (Reward: %.2f)", sid, reward)
                else:
                    logger.debug(
                        "🗑️ Discarding low-quality trajectory: %s (Reward: %.2f)", sid, reward
                    )

            except Exception as e:  # noqa: BLE001
                logger.error("Failed to process trajectory %s: %s", sid, e)

        if not golden_trajectories:
            logger.info("No golden trajectories found tonight. Skipping MLX training.")
            return {"status": "skipped", "reason": "No high-reward data"}

        # Format and save dataset
        dataset_path = self._save_dataset(golden_trajectories)
        logger.info("💾 Saved %d golden trajectories to %s", len(golden_trajectories), dataset_path)

        # Trigger actual or simulated MLX training
        avg_reward = total_reward / len(golden_trajectories)
        training_result = await self._trigger_mlx_lora()

        return {
            "status": "success",
            "trajectories_processed": len(session_ids),
            "golden_trajectories": len(golden_trajectories),
            "average_reward": round(avg_reward, 3),
            "training_result": training_result,
        }

    def _save_dataset(self, trajectories: list[Trajectory]) -> Path:
        """Saves golden trajectories in ShareGPT format for MLX-LM."""
        # ShareGPT format is optimal for instruction tuning
        formatted_json = self.collector.format_for_sft(trajectories, format_type="sharegpt")

        timestamp = int(time.time())
        file_path = self.dataset_dir / f"golden_dataset_{timestamp}.jsonl"

        # MLX-LM expects JSONL
        data = json.loads(formatted_json)
        with open(file_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

        # Also maintain a symlink to 'latest.jsonl'
        latest_link = self.dataset_dir / "latest.jsonl"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(file_path)

        return file_path

    async def _trigger_mlx_lora(self) -> dict[str, Any]:
        """
        Triggers mlx_lm.lora asynchronously.
        This alters the neural weights in real-time on Apple Silicon.
        """
        logger.info("🧠 Triggering MLX LoRA Fine-Tuning (Apple Silicon Optimization)...")

        self.adapter_path.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            "-m",
            "mlx_lm.lora",
            "--model",
            self.base_model,
            "--data",
            str(self.dataset_dir),
            "--adapter-path",
            str(self.adapter_path),
            "--iters",
            "100",
            "--batch-size",
            "2",
            "--lora-layers",
            "8",
        ]

        try:
            # We run via to_thread to not block the main CORTEX loop
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if process.returncode != 0:
                logger.error("MLX LoRA Failed: %s", process.stderr)
                return {"status": "error", "error": process.stderr[:500]}

            logger.info("✅ MLX LoRA completed successfully.")
            return {"status": "success", "output": process.stdout[-500:]}

        except subprocess.TimeoutExpired:
            logger.warning("MLX LoRA timed out.")
            return {"status": "timeout"}
        except Exception as e:  # noqa: BLE001
            logger.error("Exception during MLX execution: %s", e)
            return {"status": "error", "error": str(e)}
