#!/usr/bin/env python3
"""
CORTEX v5.2 — Agent Training Data Generator.

Processes episodic memory to extract high-reward trajectories,
formatted for Qwen2.5-Coder SFT and RL training.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

import aiosqlite

from cortex.config import DB_PATH
from cortex.extensions.episodic.main import EpisodicMemory
from cortex.extensions.training.collector import TrajectoryCollector
from cortex.extensions.training.reward_engine import RewardEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.training.data_gen")

OUTPUT_DIR = Path("/Users/borjafernandezangulo/cortex/data/training")
OUTPUT_FILE = OUTPUT_DIR / "agent_trajectories.jsonl"


async def generate_data():
    logger.info("Connecting to CORTEX DB at %s", DB_PATH)

    if not os.path.exists(DB_PATH):
        logger.error("DB file not found! Please ensure CORTEX has episodes recorded.")
        return

    async with aiosqlite.connect(DB_PATH) as conn:
        episodic = EpisodicMemory(conn)
        collector = TrajectoryCollector(episodic)
        reward_engine = RewardEngine(use_tests=True)

        # 1. Get unique session IDs from the last 1000 episodes
        sql = "SELECT DISTINCT session_id FROM episodes ORDER BY created_at DESC LIMIT 100"
        async with conn.execute(sql) as cursor:
            rows = await cursor.fetchall()
            session_ids = [row[0] for row in rows]

        logger.info("Processing %s sessions: %s", len(session_ids), session_ids)

        trajectories = []
        for sid in session_ids:
            try:
                traj = await collector.collect_session_trajectory(sid)
                if traj and traj.actions:
                    # Calculate reward
                    traj.reward = reward_engine.calculate_reward(traj)
                    logger.info(
                        "Session %s -> Reward: %.2f, Actions: %s",
                        sid,
                        traj.reward,
                        len(traj.actions),
                    )

                    # We only keep trajectories with positive reward for SFT
                    if traj.reward > 0.1:
                        trajectories.append(traj)
                        logger.info("Added trajectory for %s (Reward: %.2f)", sid, traj.reward)
            except Exception as e:
                logger.warning("Failed to process session %s: %s", sid, e)

        # 2. Export to SFT format
        if not trajectories:
            logger.warning("No high-reward trajectories found.")
            return

        sft_data_json = collector.format_for_sft(trajectories, format_type="sharegpt")
        sft_data = json.loads(sft_data_json)

        # Save as JSONL
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            for item in sft_data:
                f.write(json.dumps(item) + "\n")

        logger.info("Successfully exported %s trajectories to %s", len(trajectories), OUTPUT_FILE)


if __name__ == "__main__":
    asyncio.run(generate_data())
