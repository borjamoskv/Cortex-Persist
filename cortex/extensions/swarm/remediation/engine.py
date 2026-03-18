"""LEGION-Ω 100-Agent Remediation Engine.

Orchestrates the Blue (remediation) and Red (siege) teams.
1. Diagnosis: Find defects via SQL.
2. Blue Proposal: Agent/Specialist proposes a deterministic fix.
3. Red Siege: Mirror Agent/Specialists attack the fix to verify integrity.
4. Persistence: Commit if Red passes, rollback/quarantine if Red rejects.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.extensions.swarm.remediation.blue_team import BLUE_TEAM
from cortex.extensions.swarm.remediation.diagnosis import DiagnosisClassifier
from cortex.extensions.swarm.remediation.red_team import RED_TEAM

logger = logging.getLogger("cortex.swarm.remediation.engine")


@dataclass
class RemediationReport:
    """Consolidated report of a remediation swarm execution."""

    db_path: str
    dry_run: bool
    total_facts_scanned: int
    total_issues_found: int
    fixes_applied: int
    fixes_rejected: int
    fixes_failed: int
    details: list[dict[str, Any]]


class LegionRemediationEngine:
    """The 100-agent swarm orchestrator."""

    def __init__(self, db_path: str, dry_run: bool = True) -> None:
        self.db_path = db_path
        self.dry_run = dry_run
        self.classifier = DiagnosisClassifier(db_path)

    async def execute(self) -> RemediationReport:
        """Run the full 100-agent remediation cycle."""
        logger.info(
            "Starting 100-agent remediation swarm [dry_run=%s] on %s",
            self.dry_run,
            self.db_path,
        )

        diagnoses = await self.classifier.scan_all()
        report_details: list[dict[str, Any]] = []
        applied_count = 0
        rejected_count = 0
        failed_count = 0

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            for diag in diagnoses:
                fact_id = diag.fact_id
                battalion_id = diag.battalion

                # 1. Blue Team Proposal
                blue_battalion = BLUE_TEAM.get(battalion_id)
                if not blue_battalion:
                    logger.warning("No Blue battalion for %s", battalion_id)
                    continue

                blue_agent = blue_battalion.select_agent(diag)
                blue_result = await blue_agent.remediate(diag, db, dry_run=self.dry_run)

                if not blue_result.success:
                    failed_count += 1
                    report_details.append({
                        "fact_id": fact_id,
                        "battalion": battalion_id,
                        "status": "FAILED",
                        "blue": asdict(blue_result),
                    })
                    continue

                # 2. Red Team Siege
                # Fetch full fact state after Blue's potential (dry) mutation
                # In dry-run, we just fetch the original fact and assume the fix would be applied.
                cursor = await db.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
                fact_row = await cursor.fetchone()
                fact = dict(fact_row) if fact_row else {}

                red_battalion = RED_TEAM.get(battalion_id)
                if not red_battalion:
                    logger.warning("No Red battalion for %s", battalion_id)
                    # If no Red, we default to rejection for safety in this swarm
                    rejected_count += 1
                    continue

                red_agent_idx = int(blue_agent.agent_id.split("-")[2]) - 1 # Mirror agent
                red_agent = red_battalion.agents[red_agent_idx]
                siege_results = await red_agent.siege(fact, blue_result, db)

                passed = all(sr.passed for sr in siege_results)

                if passed:
                    if not self.dry_run:
                        await db.commit()
                    applied_count += 1
                    status = "APPLIED" if not self.dry_run else "DRY_RUN_OK"
                else:
                    if not self.dry_run:
                        await db.rollback()
                    rejected_count += 1
                    status = "REJECTED"

                report_details.append({
                    "fact_id": fact_id,
                    "battalion": battalion_id,
                    "status": status,
                    "blue": asdict(blue_result),
                    "red": [asdict(sr) for sr in siege_results],
                })

        report = RemediationReport(
            db_path=self.db_path,
            dry_run=self.dry_run,
            total_facts_scanned=0,  # Updated below
            total_issues_found=len(diagnoses),
            fixes_applied=applied_count,
            fixes_rejected=rejected_count,
            fixes_failed=failed_count,
            details=report_details,
        )

        # Get total fact count for context
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM facts")
            row = await cursor.fetchone()
            report.total_facts_scanned = row[0] if row else 0

        logger.info(
            "Remediation complete. Applied: %d, Rejected: %d, Failed: %d",
            applied_count,
            rejected_count,
            failed_count,
        )
        return report

    def save_report(self, report: RemediationReport, output_path: str | Path) -> None:
        """Serialize report to JSON."""
        with open(output_path, "w") as f:
            json.dump(asdict(report), f, indent=2)
        logger.info("Report saved to %s", output_path)
