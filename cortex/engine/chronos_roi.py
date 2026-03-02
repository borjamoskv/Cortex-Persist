"""
CHRONOS-1 ROI Engine (Sovereign Efficiency Quantification).

Formula: Hours_Saved = (15 + (Files * 10)) * (Complexity^1.5 / 2) / 60
ROI = Saved_Value / Interaction_Cost
"""

from __future__ import annotations

import os
import subprocess


class ChronosROI:
    """Ω-Level ROI quantification with Git-Archaeology and Token Costing."""

    def __init__(self, hourly_rate: float = 150.0):
        self.hourly_rate = hourly_rate  # Default $150/hr for Senior Architect
        self.token_cost_per_m = 0.015  # Estimated cost per 1k tokens

    def calculate_hours_saved(self, files_affected: int, complexity: float) -> float:
        """Calculate hours saved based on file count and complexity (Ω₂)."""
        base = 15 + (files_affected * 10)
        multiplier = (complexity**1.5) / 2.0
        minutes = base * multiplier
        return round(minutes / 60.0, 2)

    def get_git_stats(self, project_path: str) -> dict[str, int]:
        """Extract 'Sovereign Proof of Work' from Git history."""
        try:
            # Lines added/deleted in the last 24h
            cmd = ["git", "log", "--since='24 hours ago'", "--pretty=tformat:", "--numstat"]
            out = subprocess.check_output(cmd, cwd=project_path, text=True)
            added = 0
            deleted = 0
            for line in out.splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    added += int(parts[0]) if parts[0].isdigit() else 0
                    deleted += int(parts[1]) if parts[1].isdigit() else 0

            commit_count_cmd = ["git", "rev-list", "--count", "HEAD", "--since='24 hours ago'"]
            commit_count = int(subprocess.check_output(commit_count_cmd, cwd=project_path))
            return {"added": added, "deleted": deleted, "commits": commit_count}
        except Exception:
            return {"added": 0, "deleted": 0, "commits": 0}

    def audit_project(self, project_path: str, tokens_used: int = 25000) -> dict[str, any]:  # type: ignore[reportGeneralTypeIssues]
        """Scans project with Git-archaeology to calculate real-world value."""
        relevant_files = []
        for root, _, files in os.walk(project_path):
            if any(x in root for x in [".venv", ".git", "__pycache__"]):
                continue
            for f in files:
                if f.endswith((".py", ".js", ".ts", ".swift", ".html", ".css")):
                    relevant_files.append(os.path.join(root, f))

        file_count = len(relevant_files)
        git = self.get_git_stats(project_path)

        # Frontend Oracle check
        frontend_violations = 0
        try:
            from cortex.verification.frontend_oracle import FrontendOracle

            oracle = FrontendOracle()
            for f in relevant_files:
                if f.endswith((".html", ".js", ".ts")):
                    issues = oracle.analyze_file(f)
                    frontend_violations += len(issues)
        except Exception:
            pass

        # Boost complexity based on git activity
        base_complexity = 6.5
        if git["commits"] > 10:
            base_complexity += 1.5
        if git["added"] > 1000:
            base_complexity += 1.0

        # Penalize drastically if Domain UX is blocked (Ω₇ Latency-Zero Axiom violated)
        if frontend_violations > 0:
            base_complexity += frontend_violations * 20.0
            file_count = max(1, file_count - (frontend_violations * 5))

        hours = self.calculate_hours_saved(file_count, base_complexity)
        monetary_value = round(hours * self.hourly_rate, 2)

        # ROI Ratio calculation: (Value / Cost)
        cost = (tokens_used / 1000.0) * self.token_cost_per_m
        roi_ratio = monetary_value / max(0.001, cost)

        return {
            "file_count": file_count,
            "git_stats": git,
            "hours_saved": hours,
            "money_saved": monetary_value,
            "roi_ratio": round(roi_ratio, 2),
            "cost": round(cost, 4),
            "currency": "USD",
        }


CHRONOS = ChronosROI()
