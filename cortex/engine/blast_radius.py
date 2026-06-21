# [C5-REAL] Exergy-Maximized
"""
CHRONOS-1 ROI Engine (Sovereign Efficiency Quantification).

KAIROS-Ω: The Time Economist.
Quantifies human time saved, persists metrics to CORTEX,
and emits signals to the bus for observability.

Formula: Hours_Saved = (15 + (Files * 10)) * (Complexity^1.5 / 2) / 60
ROI = Saved_Value / Interaction_Cost
"""

from __future__ import annotations

import logging
import os
import sqlite3
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex.database.core import connect as db_connect

logger = logging.getLogger("cortex.chronos")

__all__ = ["CHRONOS", "ChronosROI", "ChronosReport"]


# ── Data Model ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class ChronosReport:
    """Immutable snapshot of a CHRONOS audit result."""

    file_count: int
    git_commits: int
    git_added: int
    git_deleted: int
    hours_saved: float
    money_saved: float
    roi_ratio: float
    cost: float
    currency: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for persistence."""
        return {
            "file_count": self.file_count,
            "git_commits": self.git_commits,
            "git_added": self.git_added,
            "git_deleted": self.git_deleted,
            "hours_saved": self.hours_saved,
            "money_saved": self.money_saved,
            "roi_ratio": self.roi_ratio,
            "cost": self.cost,
            "currency": self.currency,
        }

    def summary(self) -> str:
        """Human-readable CHRONOS-1 summary line."""
        return (
            f"⏱️ CHRONOS-1: Files={self.file_count} | "
            f"Human Time: {self.hours_saved}h | "
            f"Value: ${self.money_saved} | "
            f"ROI: {self.roi_ratio}x"
        )


# ── Engine ──────────────────────────────────────────────────────────

_SKIP_DIRS = frozenset(
    (".venv", ".git", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache")
)
_CODE_EXTENSIONS = (".py", ".js", ".ts", ".swift", ".html", ".css", ".rs", ".go")


class ChronosROI:
    """Ω-Level ROI quantification with Git-Archaeology and Token Costing."""

    __slots__ = ("hourly_rate", "token_cost_per_m")

    def __init__(self, hourly_rate: float = 150.0) -> None:
        self.hourly_rate = hourly_rate
        self.token_cost_per_m = 0.015

    def calculate_hours_saved(self, commits: int, lines_added: int, lines_deleted: int) -> float:
        """Calculate hours saved based strictly on physical git mutations (Ω₂)."""
        minutes = (commits * 15.0) + (lines_added * 2.0) + (lines_deleted * 1.0)
        return round(minutes / 60.0, 2)

    def get_git_stats(self, project_path: str) -> dict[str, int]:
        """Extract 'Sovereign Proof of Work' from Git history."""
        try:
            cmd = ["git", "log", "--since=24 hours ago", "--pretty=tformat:", "--numstat"]
            out = subprocess.check_output(
                cmd,
                cwd=project_path,
                text=True,
                timeout=10,
            )
            added = 0
            deleted = 0
            files_changed = set()
            for line in out.splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    added += int(parts[0]) if parts[0].isdigit() else 0
                    deleted += int(parts[1]) if parts[1].isdigit() else 0
                if len(parts) >= 3:
                    files_changed.add(parts[2])

            commit_count_cmd = ["git", "rev-list", "--count", "HEAD", "--since=24 hours ago"]
            commit_count = int(
                subprocess.check_output(
                    commit_count_cmd,
                    cwd=project_path,
                    timeout=10,
                )
            )
            return {
                "added": added,
                "deleted": deleted,
                "commits": commit_count,
                "files_changed": len(files_changed),
            }
        except (subprocess.SubprocessError, OSError, ValueError):
            return {"added": 0, "deleted": 0, "commits": 0, "files_changed": 0}

    def audit_project(
        self,
        project_path: str,
        tokens_used: int | None = None,
        db_path: str | None = None,
    ) -> ChronosReport:
        """Scan project with Git-archaeology to calculate real-world value.

        Returns a ChronosReport (immutable, typed) instead of a raw dict.
        """
        git = self.get_git_stats(project_path)
        file_count = git.get("files_changed", 0)

        # C5-REAL: Exergy is measured directly from physical mutations, not arbitrary complexity.
        hours = self.calculate_hours_saved(git["commits"], git["added"], git["deleted"])
        monetary_value = round(hours * self.hourly_rate, 2)

        # Dynamic token estimation from DB if available
        actual_tokens = 0
        if db_path and os.path.exists(db_path):
            try:
                with db_connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(llm_telemetry)")
                    columns = {row[1] for row in cursor.fetchall()}
                    if "prompt_tokens" in columns and "completion_tokens" in columns:
                        # Query tokens consumed in the last 24 hours (86400s)
                        cursor.execute(
                            "SELECT SUM(COALESCE(prompt_tokens, 0) + COALESCE(completion_tokens, 0)) "
                            "FROM llm_telemetry "
                            "WHERE timestamp >= (strftime('%s', 'now') - 86400)"
                        )
                        row = cursor.fetchone()
                        if row and row[0] is not None:
                            actual_tokens = int(row[0])
            except Exception as e:
                logger.warning("Dynamic token query failed: %s", e)

        # Fallback logic: No arbitrary hallucination of tokens.
        if actual_tokens > 0:
            final_tokens = actual_tokens
        else:
            final_tokens = tokens_used or 0

        cost = (final_tokens / 1000.0) * self.token_cost_per_m
        roi_ratio = monetary_value / max(0.001, cost)

        return ChronosReport(
            file_count=file_count,
            git_commits=git["commits"],
            git_added=git["added"],
            git_deleted=git["deleted"],
            hours_saved=hours,
            money_saved=monetary_value,
            roi_ratio=round(roi_ratio, 2),
            cost=round(cost, 4),
        )

    # ── Observability Loop (NEW - closes the blind oracle gap) ──────

    def persist_report(
        self,
        report: ChronosReport,
        db_path: str,
        project: str = "system",
    ) -> int | None:
        """Persist a CHRONOS report as a CORTEX fact + emit signal.

        This closes the observability loop - CHRONOS metrics are now
        part of the CORTEX knowledge graph, not a dead-end calculation.
        """
        try:
            with db_connect(db_path) as conn:
                # 1. Store as fact (sync path for simplicity)
                from cortex.memory.temporal import now_iso

                ts = now_iso()
                content = report.summary()
                meta_json = str(report.to_dict()).replace("'", '"')

                cursor = conn.execute(
                    "INSERT INTO facts (tenant_id, project, content, fact_type, tags, confidence,"
                    " valid_from, source, meta, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "default",
                        project,
                        content,
                        "knowledge",
                        '["chronos", "roi", "metrics"]',
                        "observed",
                        ts,
                        "chronos-roi",
                        meta_json,
                        ts,
                        ts,
                    ),
                )
                fact_id: int = cursor.lastrowid  # type: ignore[assignment]

                # 2. Emit signal to bus
                from cortex.extensions.signals.bus import SignalBus

                bus = SignalBus(conn)
                bus.emit(
                    "chronos:audit",
                    payload=report.to_dict(),
                    source="chronos-roi",
                    project=project,
                )

                logger.info("CHRONOS report persisted as fact #%d: %s", fact_id, report.summary())
                return fact_id

        except (sqlite3.Error, OSError, ImportError) as e:
            logger.warning("CHRONOS persistence failed (degraded mode): %s", e)
            return None

    def audit_and_persist(
        self,
        project_path: str,
        db_path: str,
        project: str = "system",
        tokens_used: int | None = None,
    ) -> ChronosReport:
        """Full audit cycle: scan → calculate → persist → signal.

        This is the recommended entry point for the observability loop.
        """
        report = self.audit_project(project_path, tokens_used, db_path=db_path)
        self.persist_report(report, db_path, project)
        return report


CHRONOS = ChronosROI()
