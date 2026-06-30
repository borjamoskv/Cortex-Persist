# [C5-REAL] Exergy-Maximized
"""
Autonomous Training Daemon (Sleep Cycle).
Tracks daily session trajectories, triggers Test-Time Training (TTT),
verifies output LoRA adapters, and registers them.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from babylon60.extensions.training.ttt_engine import TTTEngine
from babylon60.extensions.training.verifier import AdapterVerifier

logger = logging.getLogger("cortex_extensions.training.daemon")


class AutonomousTrainingDaemon:
    """
    Nocturnal training daemon. Runs in the background, consolidation phase.
    """

    def __init__(
        self,
        episodic_memory: Any,
        interval_seconds: int = 3600,
        base_model: str | None = None,
    ) -> None:
        self.episodic_memory = episodic_memory
        self.interval_seconds = interval_seconds
        self.verifier = AdapterVerifier()
        self.ttt_engine = TTTEngine(episodic_memory)

        # Base model configuration matching TTTEngine
        self.base_model = base_model or self.ttt_engine.base_model

        # Directories
        self.training_dir = Path.home() / ".cortex" / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)

        self.consolidated_sessions_file = self.training_dir / "consolidated_sessions.json"
        self.verified_adapter_file = self.training_dir / "verified_adapter.json"

        # Background loop task
        self.is_running = False
        self._task: asyncio.Task | None = None

    async def get_all_session_ids(self) -> list[str]:
        """Queries episodic memory for all distinct session IDs."""
        try:
            if hasattr(self.episodic_memory, "_conn"):
                async with self.episodic_memory._conn.execute(
                    "SELECT DISTINCT session_id FROM episodes"
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows if row[0]]
        except Exception as e:
            logger.error("Failed to query distinct session IDs: %s", e)
        return []

    def load_consolidated_sessions(self) -> set[str]:
        """Loads session IDs that have already been consolidated."""
        if not self.consolidated_sessions_file.exists():
            return set()
        try:
            with open(self.consolidated_sessions_file, encoding="utf-8") as f:
                data = json.load(f)
                return set(data)
        except Exception as e:
            logger.error("Failed to load consolidated sessions: %s", e)
            return set()

    def save_consolidated_sessions(self, sessions: set[str]) -> None:
        """Saves consolidated session IDs."""
        try:
            with open(self.consolidated_sessions_file, "w", encoding="utf-8") as f:
                json.dump(list(sessions), f, indent=2)
        except Exception as e:
            logger.error("Failed to save consolidated sessions: %s", e)

    def register_verified_adapter(self, adapter_path: Path, metrics: dict[str, Any]) -> None:
        """Registers the verified adapter as the active runtime adapter."""
        try:
            registry_data = {
                "adapter_path": str(adapter_path.resolve()),
                "base_model": self.base_model,
                "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "performance_metrics": metrics,
                "status": "verified",
            }
            with open(self.verified_adapter_file, "w", encoding="utf-8") as f:
                json.dump(registry_data, f, indent=2)
            logger.info("🎉 Registered verified adapter at %s", adapter_path)
        except Exception as e:
            logger.error("Failed to register verified adapter: %s", e)

    async def run_cycle(self) -> dict[str, Any]:
        """
        Executes a single cycle of the training daemon.
        1. Fetch all session IDs.
        2. Identify unconsolidated sessions.
        3. Trigger TTTEngine nocturnal consolidation on them.
        4. Verify output adapter structure and safety.
        5. Register verified adapter.
        """
        logger.info("🌙 Running autonomous training cycle...")
        all_sessions = await self.get_all_session_ids()
        consolidated = self.load_consolidated_sessions()

        unconsolidated = [sid for sid in all_sessions if sid not in consolidated]

        if not unconsolidated:
            logger.info("💤 No new sessions to consolidate.")
            return {"status": "idle", "processed_sessions": 0}

        logger.info("🧪 Found %d new sessions for consolidation.", len(unconsolidated))

        try:
            # Trigger nocturnal consolidation (MLX LoRA training subprocess)
            result = await self.ttt_engine.run_nocturnal_consolidation(unconsolidated)

            if result.get("status") == "success":
                # Verify the generated adapter
                adapter_path = self.ttt_engine.adapter_path
                verify_res = self.verifier.verify_adapter(adapter_path, self.base_model)

                if verify_res.get("success"):
                    metrics = {
                        "average_reward": result.get("average_reward", 0.0),
                        "golden_trajectories": result.get("golden_trajectories", 0),
                        "verifier_metrics": verify_res.get("metrics", {}),
                    }
                    self.register_verified_adapter(adapter_path, metrics)

                    # Mark sessions as consolidated
                    new_consolidated = consolidated.union(unconsolidated)
                    self.save_consolidated_sessions(new_consolidated)

                    return {
                        "status": "success",
                        "processed_sessions": len(unconsolidated),
                        "adapter": str(adapter_path),
                        "metrics": metrics,
                    }
                logger.error("❌ Adapter verification failed: %s", verify_res.get("error"))
                return {
                    "status": "verification_failed",
                    "error": verify_res.get("error"),
                    "processed_sessions": 0,
                }
            if result.get("status") == "skipped":
                # Even if skipped (e.g., no high reward data), we mark them as processed to avoid re-evaluating
                new_consolidated = consolidated.union(unconsolidated)
                self.save_consolidated_sessions(new_consolidated)
                logger.info("⏭️ Consolidation skipped: %s", result.get("reason"))
                return {
                    "status": "skipped",
                    "reason": result.get("reason"),
                    "processed_sessions": len(unconsolidated),
                }
            logger.error("❌ Consolidation pipeline failed: %s", result.get("error"))
            return {
                "status": "failed",
                "error": result.get("error"),
                "processed_sessions": 0,
            }

        except Exception as e:
            logger.error("Exception during training cycle: %s", e)
            return {"status": "error", "error": str(e), "processed_sessions": 0}

    async def start(self) -> None:
        """Starts the background loop."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("🚀 Autonomous Training Daemon started.")

    async def stop(self) -> None:
        """Stops the background loop."""
        if not self.is_running:
            return
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
        logger.info("🛑 Autonomous Training Daemon stopped.")

    async def _loop(self) -> None:
        """Main loop that calls run_cycle periodically."""
        while self.is_running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error("Error in daemon loop: %s", e)
            await asyncio.sleep(self.interval_seconds)
