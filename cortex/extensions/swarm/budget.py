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

# from cortex.database.core import connect as db_connect

logger = logging.getLogger("cortex.extensions.swarm.budget")

# Estimated costs per 1k tokens (subject to change)
# Defaulting to conservative pricing for GPT-4 level models
COST_PRICING = {
    "gemini": {"input": 0.000125, "output": 0.000375},
    "qwen": {"input": 0.00007, "output": 0.00028},
    "openai": {"input": 0.005, "output": 0.015},
    "anthropic": {"input": 0.003, "output": 0.015},
    "default": {"input": 0.001, "output": 0.003},
}


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
        with sqlite3.connect(self.db_path, timeout=5) as conn:
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
            with sqlite3.connect(self.db_path, timeout=5) as conn:
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

    def get_mission_budget(self, mission_id: str) -> MissionBudget | None:
        """Retrieve current budget state for a mission."""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
