# [C5-REAL] Exergy-Maximized
"""
Test-Time Training (TTT) Engine.
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

# Secure absolute offline autarchy for HF model loading inside training tasks
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_CACHE"] = os.path.expanduser("~/.babylon60/huggingface")

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from babylon60.extensions.training.collector import Trajectory, TrajectoryCollector
from babylon60.extensions.training.reward_engine import RewardEngine

logger = logging.getLogger("babylon60_extensions.training.ttt")


class TTTEngine:
    """
    Test-Time Training Orchestrator.
    Filters high-reward trajectories and triggers local MLX fine-tuning.
    """

    def __init__(self, episodic_memory: Any, triad: Any = None):
        self.collector = TrajectoryCollector(episodic_memory)
        self.rewarder = RewardEngine(use_tests=True)

        self.dataset_dir = Path.home() / ".babylon60" / "training" / "datasets"
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

        # We target the Qwen2.5 base model used by BABYLON-60
        self.base_model = os.getenv(
            "CORTEX_BASE_MODEL_PATH", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        )
        self.adapter_path = Path.home() / ".babylon60" / "training" / "adapters"

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

                reward = self.rewarder.calculate_reward(traj)

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
        """Saves golden trajectories in ShareGPT/messages format for MLX-LM."""
        # Format trajectories into JSON format
        formatted_json = self.collector.format_for_sft(trajectories, format_type="sharegpt")
        data = json.loads(formatted_json)

        # Map 'conversations' key to 'messages' for MLX-LM compatibility
        mapped_entries = []
        for entry in data:
            if "conversations" in entry:
                mapped_entries.append({"messages": entry["conversations"]})
            else:
                mapped_entries.append(entry)

        train_path = self.dataset_dir / "train.jsonl"
        valid_path = self.dataset_dir / "valid.jsonl"
        test_path = self.dataset_dir / "test.jsonl"

        # Append golden trajectories incrementally to the train set
        # This merges user corrections with static compiled knowledge
        existing_lines = []
        if train_path.exists():
            try:
                with open(train_path, encoding="utf-8") as f:
                    existing_lines = [line.strip() for line in f if line.strip()]
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to read existing train.jsonl: %s", e)

        # Write combined dataset
        try:
            with open(train_path, "w", encoding="utf-8") as f:
                # Keep existing lines
                for line in existing_lines:
                    f.write(line + "\n")
                # Append new golden trajectories
                for entry in mapped_entries:
                    f.write(json.dumps(entry) + "\n")
            logger.info("Injected %d golden trajectories into train.jsonl", len(mapped_entries))
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to write to train.jsonl: %s", e)

        # Ensure valid.jsonl and test.jsonl exist with at least 1 entry to satisfy MLX-LM
        for path in [valid_path, test_path]:
            if not path.exists() or path.stat().st_size == 0:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        if mapped_entries:
                            f.write(json.dumps(mapped_entries[0]) + "\n")
                        elif existing_lines:
                            f.write(existing_lines[0] + "\n")
                        else:
                            # Strict fallback dummy matching format
                            dummy = {
                                "messages": [
                                    {"role": "system", "content": "stub"},
                                    {"role": "user", "content": "ping"},
                                    {"role": "assistant", "content": "pong"},
                                ]
                            }
                            f.write(json.dumps(dummy) + "\n")
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to write split file %s: %s", path, e)

        # Maintain a log of the nocturnal trajectories
        timestamp = int(time.time())
        log_file = self.dataset_dir / f"golden_dataset_{timestamp}.jsonl"
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                for entry in mapped_entries:
                    f.write(json.dumps(entry) + "\n")
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to save golden log: %s", e)

        return train_path

    async def _trigger_mlx_lora(self) -> dict[str, Any]:
        """
        Triggers mlx_lm.lora training asynchronously.
        Alters neural weights using Apple Silicon Metal optimization.
        """
        logger.info("🧠 Triggering MLX LoRA Fine-Tuning (Apple Silicon Optimization)...")

        self.adapter_path.mkdir(parents=True, exist_ok=True)

        # Optimized cmd arguments avoiding OOM/NaN and using updated subcommand syntax
        cmd = [
            sys.executable,
            "-m",
            "mlx_lm",
            "lora",
            "--model",
            self.base_model,
            "--train",
            "--data",
            str(self.dataset_dir),
            "--adapter-path",
            str(self.adapter_path),
            "--fine-tune-type",
            "lora",
            "--optimizer",
            "adamw",
            "--mask-prompt",
            "--num-layers",
            "16",
            "--iters",
            "50",  # Optimized iterations for nocturnal cycle
            "--batch-size",
            "1",  # Lower batch size to prevent OOM
            "--grad-accumulation-steps",
            "2",  # Virtual batch size = 2
            "--val-batches",
            "5",  # Speed up validation checks
            "--max-seq-length",
            "1280",  # Avoid truncation
            "--grad-checkpoint",  # Enable memory optimizations
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
