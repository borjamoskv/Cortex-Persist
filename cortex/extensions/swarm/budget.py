"""CORTEX v7.0 — Swarm Budget Manager.

Tracks token consumption and costs per mission using SQLite.
Integrates with LLMProvider to capture actual 'usage' metrics.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from cortex.database.core import connect as db_connect

logger = logging.getLogger("cortex.extensions.swarm.budget")

# 2026 Sovereign Pricing (Exergy-Optimized)
COST_PRICING = {
    "gemini": {"input": 0.000075, "output": 0.000225},  # Flash 2.5
    "qwen": {"input": 0.00005, "output": 0.0002},  # Qwen 2.5
    "openai": {"input": 0.0025, "output": 0.01},  # GPT-4o
    "anthropic": {"input": 0.003, "output": 0.015},
    "default": {"input": 0.0001, "output": 0.0003},
}

HARD_LIMIT_USD = 0.10  # Ω₃: Per-mission exergy ceiling


@dataclass(frozen=True)
class MissionBudget:
    mission_id: str
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    request_count: int
    last_update: float


class SwarmBudgetManager:
    """Manages token budgets and costs for decentralized swarms."""

    def __init__(self, db_path: str = "~/.cortex/budget.db"):
        self.db_path = Path(db_path).expanduser()
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with db_connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mission_budget (
                    mission_id           TEXT PRIMARY KEY,
                    total_input_tokens   INTEGER DEFAULT 0,
                    total_output_tokens  INTEGER DEFAULT 0,
                    total_cost_usd       REAL DEFAULT 0,
                    request_count        INTEGER DEFAULT 0,
                    last_update          REAL
                )
            """)

    def report_usage(self, mission_id: str, provider: str, input_tokens: int, output_tokens: int):
        """Record token usage for a specific mission and provider."""
        if not mission_id:
            return

        pricing = COST_PRICING.get(provider, COST_PRICING["default"])
        cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

        now = time.time()
        try:
            with db_connect(str(self.db_path)) as conn:
                conn.execute(
                    """
                    INSERT INTO mission_budget
                    (mission_id, total_input_tokens, total_output_tokens,
                     total_cost_usd, request_count, last_update)
                    VALUES (?, ?, ?, ?, 1, ?)
                    ON CONFLICT(mission_id) DO UPDATE SET
                        total_input_tokens = total_input_tokens + excluded.total_input_tokens,
                        total_output_tokens = total_output_tokens + excluded.total_output_tokens,
                        total_cost_usd = total_cost_usd + excluded.total_cost_usd,
                        request_count = request_count + 1,
                        last_update = excluded.last_update
                """,
                    (mission_id, input_tokens, output_tokens, cost, now),
                )
                logger.debug(
                    "Budget: %d tokens ($%.4f) reported for mission %s",
                    input_tokens + output_tokens,
                    cost,
                    mission_id,
                )
        except sqlite3.Error as e:
            logger.error("Budget: Failed to report usage: %s", e)

        # Immediate enforcement of Ω₃
        self.check_budget(mission_id)

    def check_budget(self, mission_id: str):
        """Enforce Ω₃: Raise error if mission exceeds hard exergy limit."""
        budget = self.get_mission_budget(mission_id)
        if budget and budget.total_cost_usd >= HARD_LIMIT_USD:
            logger.critical(
                "🛑 [Ω₃] EXERGY EXHAUSTED: Mission %s reached cost limit ($%.4f)",
                mission_id,
                budget.total_cost_usd,
            )
            raise RuntimeError(
                f"Exergy exhaustion: Mission {mission_id} exceeded ${HARD_LIMIT_USD} limit."
            )

    def get_mission_budget(self, mission_id: str) -> MissionBudget | None:
        """Retrieve current budget state for a mission."""
        try:
            with db_connect(str(self.db_path)) as conn:
                row = conn.execute(
                    """SELECT mission_id, total_input_tokens, total_output_tokens,
                              total_cost_usd, request_count, last_update
                       FROM mission_budget WHERE mission_id = ?""",
                    (mission_id,),
                ).fetchone()
                if row:
                    return MissionBudget(*row)
        except sqlite3.Error as e:
            logger.error("Budget: Failed to fetch: %s", e)
        return None

    def list_missions(self) -> list[MissionBudget]:
        """List all missions tracked in the budget database."""
        try:
            with db_connect(str(self.db_path)) as conn:
                rows = conn.execute(
                    "SELECT * FROM mission_budget ORDER BY last_update DESC"
                ).fetchall()
                return [MissionBudget(*row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Budget: Failed to list: %s", e)
            return []


# Single instance for the process
_instance = None


def get_budget_manager() -> SwarmBudgetManager:
    global _instance
    if _instance is None:
        _instance = SwarmBudgetManager()
    return _instance
