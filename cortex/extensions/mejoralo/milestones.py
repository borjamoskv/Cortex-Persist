"""Milestone Manager — Detect and persist record-breaking achievements."""

from __future__ import annotations

import json
import logging

from cortex.database.core import connect as db_connect
from cortex.extensions.mejoralo.models import Milestone
from cortex.memory.temporal import now_iso

logger = logging.getLogger("cortex.mejoralo.milestones")

SCORE_THRESHOLDS = [80, 90, 95, 100]
YIELD_THRESHOLDS = [100, 200, 420, 1000]


class MilestoneManager:
    """Manages detection and persistence of project milestones."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def get_achieved_milestones(self, project: str) -> list[Milestone]:
        """Retrieve all achieved milestones for a project from the ledger."""
        milestones = []
        try:
            with db_connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT metadata FROM facts WHERE project = ? AND fact_type = 'milestone'",
                    (project,),
                )
                rows = cursor.fetchall()
                for row in rows:
                    try:
                        data = json.loads(row[0])
                        milestones.append(
                            Milestone(
                                name=data["name"],
                                target=data["target"],
                                unit=data["unit"],
                                achieved_at=data["achieved_at"],
                                message=data["message"],
                                project=project,
                            )
                        )
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            logger.error("Failed to retrieve milestones for %s: %s", project, e)
        return milestones

    def check_score_milestones(
        self, project: str, current_score: float, achieved_milestones: list[Milestone] | None = None
    ) -> list[Milestone]:
        """Check if any new score milestones have been reached."""
        if achieved_milestones is None:
            achieved_milestones = self.get_achieved_milestones(project)

        achieved_targets = {m.target for m in achieved_milestones if m.unit == "score"}

        new_milestones = []
        for target in SCORE_THRESHOLDS:
            if current_score >= target and target not in achieved_targets:
                name = "Foundational" if target == 80 else \
                       "Advanced" if target == 90 else \
                       "Inmejorable" if target == 95 else "Sovereign Standard"

                m = Milestone(
                    name=f"{name} ({target}+)",
                    target=float(target),
                    unit="score",
                    achieved_at=now_iso(),
                    message=f"Project '{project}' reached {name} status with a score of {target}.",
                    project=project,
                )
                if self._persist_milestone(m):
                    new_milestones.append(m)

        return new_milestones

    def check_yield_milestones(
        self, project: str, current_yield: float, achieved_milestones: list[Milestone] | None = None
    ) -> list[Milestone]:
        """Check if any new yield milestones have been reached."""
        if achieved_milestones is None:
            achieved_milestones = self.get_achieved_milestones(project)

        achieved_targets = {m.target for m in achieved_milestones if m.unit == "hours"}

        new_milestones = []
        for target in YIELD_THRESHOLDS:
            if current_yield >= target and target not in achieved_targets:
                name = "Standard 100h" if target == 100 else \
                       "Sovereign 200h" if target == 200 else \
                       "High Entropy 420h" if target == 420 else "Kiloyield 1000h"

                m = Milestone(
                    name=name,
                    target=float(target),
                    unit="hours",
                    achieved_at=now_iso(),
                    message=f"Project '{project}' secured {target}h of verified compound yield.",
                    project=project,
                )
                if self._persist_milestone(m):
                    new_milestones.append(m)

        return new_milestones

    def _persist_milestone(self, milestone: Milestone) -> bool:
        """Persist a milestone as a CORTEX fact."""
        try:
            ts = now_iso()
            meta = {
                "name": milestone.name,
                "target": milestone.target,
                "unit": milestone.unit,
                "achieved_at": milestone.achieved_at,
                "message": milestone.message,
            }

            with db_connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO facts (tenant_id, project, content, fact_type, tags, confidence, "
                    "valid_from, source, metadata, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "default",
                        milestone.project,
                        f"MILESTONE REACHED: {milestone.name}",
                        "milestone",
                        json.dumps(["milestone", milestone.unit]),
                        "observed",
                        ts,
                        "milestone-manager",
                        json.dumps(meta),
                        ts,
                        ts,
                    ),
                )
            logger.info("Milestone persisted: %s for %s", milestone.name, milestone.project)
            return True
        except Exception as e:
            logger.error("Failed to persist milestone %s: %s", milestone.name, e)
            return False
