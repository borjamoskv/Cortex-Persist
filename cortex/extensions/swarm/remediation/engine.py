# ── Sovereign Metabolic Trigger: Legion Remediation Engaged ──────────
"""LEGION-Ω 2500-Agent Remediation Engine (Hyper-Parallelized).

Orchestrates the Blue (remediation) and Red (siege) teams.
1. Diagnosis: Find defects via SQL.
2. Pre-Filter: Skip unfixable diagnoses (B2).
3. Blue Proposal: Agent/Specialist proposes a deterministic fix.
4. Red Siege: Mirror Agent/Specialists attack the fix (parallel, B1).
5. Persistence: Commit if Red passes, no per-fact rollback (B4).

Architecture:
- B1: Red Team specialists execute in parallel (asyncio.gather)
- B2: Unfixable diagnoses pre-filtered before pipeline entry
- B3: Pipeline overlap (inference N+1 during commit N)
- B4: Batch-level transaction management (no per-fact rollback)
- B5: Separate read/write DB connections to avoid cursor interleaving
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.agents.builtins.consignatario_agent import ConsignatarioAgent
from cortex.agents.manifest import AgentManifest
from cortex.database.core import connect_async_ctx
from cortex.engine.poet import CommitPoet
from cortex.extensions.swarm.remediation.blue_team import BLUE_TEAM
from cortex.extensions.swarm.remediation.diagnosis import (
    Diagnosis,
    DiagnosisClassifier,
)
from cortex.extensions.swarm.remediation.red_team import RED_TEAM
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.writer import LedgerWriter

logger = logging.getLogger("cortex.swarm.remediation.engine")


def _apply_fix_in_memory(
    fact: dict[str, Any],
    fix_sql: str | None,
    fix_params: tuple | None,
) -> dict[str, Any]:
    """Simulate SQL UPDATE on a fact dict without DB write.

    Parses the fix_sql to extract column assignments and applies
    the corresponding fix_params values to the dict. This allows
    Red Team to validate the post-fix state before the actual
    SQL is committed.

    If fix_sql is None or unparseable, returns the original dict
    unchanged (fail-safe: Red validates pre-fix state as before).
    """
    if not fix_sql or not fix_params:
        return fact

    result = dict(fact)

    # Parse "UPDATE facts SET col1 = ?, col2 = ? WHERE id = ?"
    match = re.match(
        r"UPDATE\s+\w+\s+SET\s+(.+?)\s+WHERE",
        fix_sql,
        re.IGNORECASE,
    )
    if not match:
        return fact

    assignments = match.group(1)
    cols = [
        a.strip().split("=")[0].strip()
        for a in assignments.split(",")
    ]

    # Last param is typically the WHERE id = ? value
    value_params = fix_params[: len(cols)]
    for col, val in zip(cols, value_params, strict=False):
        result[col] = val

    return result


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
    """The 2500-agent swarm orchestrator (Hyper-Parallelized)."""

    def __init__(
        self,
        db_path: str,
        dry_run: bool = True,
        engine: Any = None,
    ) -> None:
        self.db_path = db_path
        self.dry_run = dry_run
        self.engine = engine
        self.classifier = DiagnosisClassifier(db_path)
        # Consignatario Manifest
        manifest = AgentManifest(
            agent_id="consignatario-01",
            purpose="Sovereign Ledger Consignment",
            tenant_id="swarm",
        )
        self.consignatario = ConsignatarioAgent(manifest=manifest, bus=None)
        self.poet = CommitPoet()

        # Ledger Infrastructure
        self.batch_size = 50
        store = LedgerStore(db_path=db_path)
        queue = EnrichmentQueue(store=store)
        self.ledger = LedgerWriter(store=store, queue=queue)

    async def execute(self) -> RemediationReport:
        """Run the full remediation cycle (Hyper-Parallelized).

        Optimizations applied:
        - B2: Pre-filter unfixable diagnoses
        - B5: Read/Write connection split
        - B1: Parallel Red Team siege
        - B3: Pipeline overlap
        - B4: No per-fact rollback
        """
        logger.info(
            "Starting LEGION-Ω Hyper-Parallel Swarm [dry_run=%s] on %s",
            self.dry_run,
            self.db_path,
        )

        diagnoses = await self.classifier.scan_all()
        report_details: list[dict[str, Any]] = []
        applied_count = 0
        rejected_count = 0
        failed_count = 0

        # ── B2: Pre-filter unfixable diagnoses ──────────────────
        fixable: list[Diagnosis] = []
        unfixable: list[Diagnosis] = []
        functional_battalions = {"B06_SEMANTIC", "B04_ORPHAN"}

        for d in diagnoses:
            if d.fix_sql is not None:
                fixable.append(d)
            elif d.battalion in functional_battalions and self.engine:
                fixable.append(d)
            else:
                unfixable.append(d)

        # Emit FAILED for unfixable immediately (no pipeline cost)
        for d in unfixable:
            failed_count += 1
            report_details.append(
                {
                    "fact_id": d.fact_id,
                    "battalion": d.battalion,
                    "status": "FAILED",
                    "narrative": "No auto-fix. Requires manual review.",
                    "blue": None,
                    "red": [],
                }
            )

        logger.info(
            "Pre-filter: %d fixable, %d unfixable (skipped)",
            len(fixable),
            len(unfixable),
        )

        # Concurrency control
        semaphore = asyncio.Semaphore(self.batch_size)

        # ── B5: Write connection (batch commits only) ───────────
        async with connect_async_ctx(self.db_path) as write_db:
            write_db.row_factory = aiosqlite.Row
            await write_db.execute("PRAGMA journal_mode=WAL")
            await write_db.execute("PRAGMA synchronous=NORMAL")

            total_batches = max(
                1,
                (len(fixable) + self.batch_size - 1) // self.batch_size,
            )

            for batch_idx in range(0, len(fixable), self.batch_size):
                batch_diags = fixable[batch_idx : batch_idx + self.batch_size]
                b_applied = 0
                b_rejected = 0
                b_failed = 0

                # ── B5: Read-only conn for parallel phase ───
                async with connect_async_ctx(self.db_path, read_only=True) as read_db:
                    read_db.row_factory = aiosqlite.Row

                    async def _process(
                        diag: Diagnosis,
                    ) -> dict[str, Any] | None:
                        async with semaphore:
                            return await self._process_single(
                                diag,
                                read_db,
                                write_db,
                            )

                    tasks = [_process(d) for d in batch_diags]
                    outcomes = await asyncio.gather(*tasks)

                # Serial consignment (write_db only)
                for outcome in outcomes:
                    if not outcome:
                        continue

                    diag = outcome["diag"]
                    blue = outcome["blue"]
                    siege = outcome["siege"]
                    status = outcome["status"]
                    cur_status = status

                    if status == "FAILED":
                        failed_count += 1
                        b_failed += 1
                        narr = "Functional anomaly encountered."
                    elif status == "PASSED_NO_RED_TEAM":
                        rejected_count += 1
                        b_rejected += 1
                        cur_status = "REJECTED"
                        narr = self.poet.compose_remediation(
                            battalion=diag.battalion,
                            action=blue.action,
                            fact_id=diag.fact_id,
                        )
                    else:
                        consign_ok = await self.consignatario.authorize_and_commit(
                            db=write_db,
                            ledger=self.ledger,
                            blue_result=blue,
                            siege_results=siege,
                            dry_run=self.dry_run,
                            use_async_ledger=True,
                        )
                        if consign_ok and status == "PASSED":
                            applied_count += 1
                            b_applied += 1
                            cur_status = "APPLIED" if not self.dry_run else "DRY_RUN_OK"
                        else:
                            rejected_count += 1
                            b_rejected += 1
                            cur_status = "REJECTED"

                        narr = self.poet.compose_remediation(
                            battalion=diag.battalion,
                            action=blue.action,
                            fact_id=diag.fact_id,
                        )

                    report_details.append(
                        {
                            "fact_id": diag.fact_id,
                            "battalion": diag.battalion,
                            "status": cur_status,
                            "narrative": narr,
                            "blue": asdict(blue) if blue else None,
                            "red": [asdict(sr) for sr in siege],
                        }
                    )

                # Batch commit
                if not self.dry_run:
                    await write_db.commit()

                # Telemetry
                summary = self.poet.compose_swarm_summary(
                    applied=b_applied,
                    rejected=b_rejected,
                    failed=b_failed,
                )
                batch_num = (batch_idx // self.batch_size) + 1
                logger.info("BATCH_SUMMARY: %s", summary)
                logger.info(
                    "LEGION-Ω [Hyper-Batch %d/%d]: %s",
                    batch_num,
                    total_batches,
                    summary,
                )

        # Final report
        report = RemediationReport(
            db_path=self.db_path,
            dry_run=self.dry_run,
            total_facts_scanned=len(diagnoses),
            total_issues_found=len(diagnoses),
            fixes_applied=applied_count,
            fixes_rejected=rejected_count,
            fixes_failed=failed_count,
            details=report_details,
        )

        # Get total fact count for context
        async with connect_async_ctx(self.db_path, read_only=True) as db:
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

    async def _process_single(
        self,
        diag: Diagnosis,
        read_db: aiosqlite.Connection,
        write_db: aiosqlite.Connection,
    ) -> dict[str, Any] | None:
        """Process a single diagnosis (parallel-safe).

        Reads use read_db, writes use write_db.
        """
        fact_id = diag.fact_id
        battalion_id = diag.battalion

        # 1. Blue Team Proposal
        blue_battalion = BLUE_TEAM.get(battalion_id)
        if not blue_battalion:
            logger.warning("No Blue battalion for %s", battalion_id)
            return None
        blue_agent = blue_battalion.select_agent(diag)

        # Functional fix path (enrichment)
        if not diag.fix_sql and self.engine:
            result = await self._try_functional_fix(diag, blue_agent, read_db, write_db)
            if result is not None:
                return result

        # Standard remediation with retry
        blue_result = await self._remediate_with_retry(diag, blue_agent, write_db)

        if not blue_result or not blue_result.success:
            return {
                "diag": diag,
                "blue": blue_result,
                "siege": [],
                "status": "FAILED",
            }

        # 2. Red Team Siege (B1: parallel specialists)
        cursor = await read_db.execute(
            "SELECT * FROM facts WHERE id = ?", (fact_id,)
        )
        fact_row = await cursor.fetchone()
        fact_dict = dict(fact_row) if fact_row else {}

        # C1: Simulate post-fix state for Red Team validation.
        # Without this, Red validates pre-fix state (the defect
        # itself) and always rejects.
        simulated_fact = _apply_fix_in_memory(
            fact_dict, diag.fix_sql, diag.fix_params
        )

        red_battalion = RED_TEAM.get(battalion_id)
        if not red_battalion:
            logger.warning(
                "No Red battalion for %s", battalion_id
            )
            return {
                "diag": diag,
                "blue": blue_result,
                "siege": [],
                "status": "PASSED_NO_RED_TEAM",
            }

        # Mirror agent selection
        parts = blue_agent.agent_id.split("-")
        red_idx = int(parts[2]) - 1
        red_agent = red_battalion.agents[red_idx]
        siege_results = await red_agent.siege(
            simulated_fact, blue_result, read_db
        )

        passed = all(sr.passed for sr in siege_results)
        return {
            "diag": diag,
            "blue": blue_result,
            "siege": siege_results,
            "status": "PASSED" if passed else "REJECTED",
        }

    async def _try_functional_fix(
        self,
        diag: Diagnosis,
        blue_agent: Any,
        read_db: aiosqlite.Connection,
        write_db: aiosqlite.Connection,
    ) -> dict[str, Any] | None:
        """Attempt a functional fix (e.g., enrichment).

        Returns outcome dict on success, None to fall through.
        """
        battalion_id = diag.battalion
        fact_id = diag.fact_id

        if battalion_id != "B06_SEMANTIC" or diag.issue != "ENRICHMENT_INCOMPLETE":
            return None

        if self.dry_run:
            return None

        try:
            cursor = await read_db.execute(
                "SELECT content, project, tenant_id FROM facts WHERE id = ?",
                (fact_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            await self.engine.embeddings.enrich_fact(
                fact_id=fact_id,
                content=row["content"],
                project=row["project"],
                tenant_id=row["tenant_id"],
            )
            br = await blue_agent.remediate(diag, write_db, dry_run=self.dry_run)
            br = replace(
                br,
                success=True,
                action="ENRICHED",
                sql_executed="functional:enrich_fact",
            )
            return {
                "diag": diag,
                "blue": br,
                "siege": [],
                "status": "PASSED",
            }
        except Exception as e:
            logger.error(
                "Functional enrichment failed for %s: %s",
                fact_id,
                e,
            )
            return None

    async def _remediate_with_retry(
        self,
        diag: Diagnosis,
        blue_agent: Any,
        write_db: aiosqlite.Connection,
        max_retries: int = 3,
    ) -> Any:
        """Execute Blue remediation with retry on DB lock."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                return await blue_agent.remediate(diag, write_db, dry_run=self.dry_run)
            except aiosqlite.OperationalError as e:
                if "locked" in str(e).lower() and not self.dry_run:
                    retry_count += 1
                    await asyncio.sleep(0.1 * retry_count)
                    continue
                raise
        return None

    def save_report(
        self,
        report: RemediationReport,
        output_path: str | Path,
    ) -> None:
        """Serialize report to JSON."""
        with open(output_path, "w") as f:
            json.dump(asdict(report), f, indent=2)
        logger.info("Report saved to %s", output_path)
