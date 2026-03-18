# ── Sovereign Metabolic Trigger: Legion Remediation Engaged ────────────────────────
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
from dataclasses import asdict, dataclass, replace
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

    def __init__(self, db_path: str, dry_run: bool = True, engine: Any = None) -> None:
        self.db_path = db_path
        self.dry_run = dry_run
        self.engine = engine
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

                # Special Handling for Functional Fixes (B06, B04)
                if not diag.fix_sql and self.engine:
                    if battalion_id == "B06_SEMANTIC" and diag.issue == "ENRICHMENT_INCOMPLETE":
                        if not self.dry_run:
                            try:
                                # Fetch row for enrichment context
                                cursor = await db.execute(
                                    "SELECT content, project, tenant_id FROM facts WHERE id = ?",
                                    (fact_id,),
                                )
                                row = await cursor.fetchone()
                                if row:
                                    await self.engine.embeddings.enrich_fact(
                                        fact_id=fact_id,
                                        content=row["content"],
                                        project=row["project"],
                                        tenant_id=row["tenant_id"],
                                    )
                                    blue_result = await blue_agent.remediate(
                                        diag, db, dry_run=self.dry_run
                                    )
                                    # Override result since we did the functional fix
                                    blue_result = replace(
                                        blue_result,
                                        success=True,
                                        action="ENRICHED",
                                        sql_executed="functional:enrich_fact",
                                    )
                            except Exception as e:
                                logger.error("Functional enrichment failed for %s: %s", fact_id, e)
                                # Fall through to normal remediation (which will fail)

                blue_result = await blue_agent.remediate(diag, db, dry_run=self.dry_run)

                if not blue_result.success:
                    failed_count += 1
                    report_details.append(
                        {
                            "fact_id": fact_id,
                            "battalion": battalion_id,
                            "status": "FAILED",
                            "blue": asdict(blue_result),
                        }
                    )
                    continue

                cursor = await db.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
                fact_row = await cursor.fetchone()
                fact = dict(fact_row) if fact_row else {}

                # In dry-run, simulate the fix on the fact dictionary so Red can validate the proposal
                if self.dry_run and blue_result.success and diag.fix_sql:
                    # Simple heuristic parser for "UPDATE facts SET field = ? WHERE id = ?"
                    try:
                        sql = diag.fix_sql.upper()
                        if "UPDATE FACTS SET" in sql:
                            parts = diag.fix_sql.split("SET")[1].split("WHERE")[0].split("=")
                            field_name = parts[0].strip().lower()
                            fact[field_name] = diag.fix_params[0]
                    except Exception as e:
                        logger.warning("Could not simulate fix for %s: %s", fact_id, e)

                red_battalion = RED_TEAM.get(battalion_id)
                if not red_battalion:
                    logger.warning("No Red battalion for %s", battalion_id)
                    # If no Red, we default to rejection for safety in this swarm
                    rejected_count += 1
                    continue

                red_agent_idx = int(blue_agent.agent_id.split("-")[2]) - 1  # Mirror agent
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

                report_details.append(
                    {
                        "fact_id": fact_id,
                        "battalion": battalion_id,
                        "status": status,
                        "blue": asdict(blue_result),
                        "red": [asdict(sr) for sr in siege_results],
                    }
                )

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
