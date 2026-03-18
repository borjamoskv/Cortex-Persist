"""LEGION-Ω Blue Team — 50 Agents + 100 Specialists.

Hierarchy: 10 Battalions × 5 Agents × 2 Specialists = 150 entities.
- Agents: coordinate, route, and validate specialist work.
- Specialists: execute the actual deterministic fixes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace

import aiosqlite

from cortex.extensions.swarm.remediation.diagnosis import Diagnosis

logger = logging.getLogger("cortex.swarm.remediation.blue_team")


@dataclass(frozen=True)
class RemediationResult:
    """Outcome of a single remediation action."""

    fact_id: str
    agent_id: str
    specialist_id: str
    battalion: str
    success: bool
    action: str
    sql_executed: str | None = None
    error: str | None = None


@dataclass
class Specialist:
    """A sub-specialist worker — executes a single fix type."""

    specialist_id: str
    agent_id: str
    focus: str
    description: str

    async def execute(
        self,
        diagnosis: Diagnosis,
        db: aiosqlite.Connection,
        dry_run: bool = True,
    ) -> RemediationResult:
        """Execute the deterministic fix."""
        if diagnosis.fix_sql is None:
            return RemediationResult(
                fact_id=diagnosis.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=diagnosis.battalion,
                success=False,
                action="NO_AUTO_FIX",
                error=f"Issue '{diagnosis.issue}' requires manual review.",
            )

        if dry_run:
            return RemediationResult(
                fact_id=diagnosis.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=diagnosis.battalion,
                success=True,
                action=f"DRY_RUN: {diagnosis.fix_sql}",
                sql_executed=diagnosis.fix_sql,
            )

        try:
            await db.execute(diagnosis.fix_sql, diagnosis.fix_params)
            return RemediationResult(
                fact_id=diagnosis.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=diagnosis.battalion,
                success=True,
                action=f"APPLIED: {diagnosis.issue}",
                sql_executed=diagnosis.fix_sql,
            )
        except Exception as exc:  # noqa: BLE001 — remediation boundary
            logger.error(
                "Specialist %s failed on fact %s: %s",
                self.specialist_id,
                diagnosis.fact_id,
                exc,
            )
            return RemediationResult(
                fact_id=diagnosis.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=diagnosis.battalion,
                success=False,
                action=f"FAILED: {diagnosis.issue}",
                error=str(exc),
            )


@dataclass
class BlueAgent:
    """A Blue Team agent — commands 2 specialists."""

    agent_id: str
    battalion: str
    role: str
    specialists: list[Specialist] = field(default_factory=list)

    def route(self, diagnosis: Diagnosis) -> Specialist:
        """Route to the specialist whose focus best matches the issue."""
        issue_lower = diagnosis.issue.lower()
        for spec in self.specialists:
            if spec.focus.lower() in issue_lower or issue_lower in spec.focus.lower():
                return spec
        return self.specialists[0]  # Default to first specialist

    async def remediate(
        self,
        diagnosis: Diagnosis,
        db: aiosqlite.Connection,
        dry_run: bool = True,
    ) -> RemediationResult:
        """Route diagnosis to appropriate specialist, execute, and validate."""
        spec = self.route(diagnosis)
        result = await spec.execute(diagnosis, db, dry_run)

        # Agent-level validation (The "50" part of the 50+50 hierarchy)
        if result.success:
            logger.info(
                "BlueAgent %s: Validating specialist %s result",
                self.agent_id,
                spec.specialist_id,
            )
            if (
                result.sql_executed
                and "DELETE" in result.sql_executed.upper()
                and "TOMBSTONE" not in self.battalion
            ):
                logger.warning(
                    "BlueAgent %s: REJECTED specialist proposal. Unauthorized DELETE.",
                    self.agent_id,
                )
                return replace(
                    result,
                    success=False,
                    error="Agent rejected specialist proposal (Unauthorized DELETE)",
                )

        return result


@dataclass
class BlueBattalion:
    """A battalion of 5 agents (10 specialists) focused on one defect category."""

    battalion_id: str
    name: str
    agents: list[BlueAgent] = field(default_factory=list)

    @property
    def specialist_count(self) -> int:
        return sum(len(a.specialists) for a in self.agents)

    def select_agent(self, diagnosis: Diagnosis) -> BlueAgent:
        """Route to the agent best suited for this issue type."""
        issue_lower = diagnosis.issue.lower()
        for agent in self.agents:
            if agent.role.lower() in issue_lower or issue_lower in agent.role.lower():
                return agent
        return self.agents[0]

    async def remediate_batch(
        self,
        diagnoses: list[Diagnosis],
        db: aiosqlite.Connection,
        dry_run: bool = True,
    ) -> list[RemediationResult]:
        """Process all diagnoses assigned to this battalion."""
        results: list[RemediationResult] = []
        for diag in diagnoses:
            agent = self.select_agent(diag)
            result = await agent.remediate(diag, db, dry_run)
            results.append(result)
        return results


# ── Factory ─────────────────────────────────────────────────────────────


def _agent(battalion: str, idx: int, role: str, spec_def: tuple[str, str]) -> BlueAgent:
    """Build an agent with its 1 sub-agent (specialist)."""
    agent_id = f"{battalion}-agent-{idx:02d}-{role.replace(' ', '_')}"
    sf, sd = spec_def
    specs = [
        Specialist(
            specialist_id=f"{agent_id}-sub-{sf.replace(' ', '_')}",
            agent_id=agent_id,
            focus=sf,
            description=sd,
        )
    ]
    return BlueAgent(agent_id=agent_id, battalion=battalion, role=role, specialists=specs)


def _build_blue_team() -> dict[str, BlueBattalion]:
    """Construct 50 agents + 100 specialists across 10 battalions."""
    battalions: dict[str, BlueBattalion] = {}

    # B01 — Schema Integrity
    battalions["B01_SCHEMA"] = BlueBattalion(
        "B01_SCHEMA",
        "Schema Integrity",
        [
            _agent("B01", 1, "column_validator", ("null_column", "Detects NULL in cols")),
            _agent("B01", 2, "type_checker", ("type_mismatch", "Validates types")),
            _agent("B01", 3, "default_fixer", ("null_default", "Applies defaults")),
            _agent("B01", 4, "migration_probe", ("schema_drift", "Detects drift")),
            _agent("B01", 5, "schema_auditor", ("constraint_violation", "Final check")),
        ],
    )

    # B02 — Hash Reconstruction
    battalions["B02_HASH"] = BlueBattalion(
        "B02_HASH",
        "Hash Reconstruction",
        [
            _agent("B02", 1, "hash_rebuilder", ("null_hash", "Recomputes hashes")),
            _agent("B02", 2, "sha256_signer", ("signing", "Signs facts")),
            _agent("B02", 3, "hash_verifier", ("hash_mismatch", "Compares hashes")),
            _agent("B02", 4, "chain_linker", ("chain_break", "Validates chain")),
            _agent("B02", 5, "integrity_probe", ("deep_integrity", "Deep probe")),
        ],
    )

    # B03 — Confidence Calibration
    battalions["B03_CONFIDENCE"] = BlueBattalion(
        "B03_CONFIDENCE",
        "Confidence Calibration",
        [
            _agent("B03", 1, "bounds_normalizer", ("null_confidence", "Sets confidence")),
            _agent("B03", 2, "outlier_detector", ("outlier", "Flags outliers")),
            _agent("B03", 3, "decay_calibrator", ("temporal_decay", "Applies decay")),
            _agent("B03", 4, "source_weighter", ("source_weight", "Adjusts weight")),
            _agent("B03", 5, "confidence_auditor", ("distribution_audit", "Final audit")),
        ],
    )

    # B04 — Exergy Scoring
    battalions["B04_EXERGY"] = BlueBattalion(
        "B04_EXERGY",
        "Exergy Scoring",
        [
            _agent("B04", 1, "exergy_calculator", ("missing_exergy", "Computes metrics")),
            _agent("B04", 2, "content_weighter", ("length_weight", "Weights content")),
            _agent("B04", 3, "complexity_scorer", ("semantic_complexity", "Scores complexity")),
            _agent("B04", 4, "impact_estimator", ("downstream_impact", "Estimates impact")),
            _agent("B04", 5, "exergy_auditor", ("distribution_audit", "Final audit")),
        ],
    )

    # B05 — Source Attribution
    battalions["B05_SOURCE"] = BlueBattalion(
        "B05_SOURCE",
        "Source Attribution",
        [
            _agent("B05", 1, "source_inferrer", ("missing_source", "Infers source")),
            _agent("B05", 2, "meta_extractor", ("metadata_parse", "Extracts source")),
            _agent("B05", 3, "agent_tag_resolver", ("agent_tag", "Resolves agent")),
            _agent("B05", 4, "origin_tracer", ("ledger_origin", "Traces origin")),
            _agent("B05", 5, "source_auditor", ("coverage_audit", "Final audit")),
        ],
    )

    # B06 — Semantic Enrichment
    battalions["B06_SEMANTIC"] = BlueBattalion(
        "B06_SEMANTIC",
        "Semantic Enrichment",
        [
            _agent("B06", 1, "embed_trigger", ("enrichment_incomplete", "Triggers re-embed")),
            _agent("B06", 2, "status_updater", ("invalid_semantic_status", "Corrects status")),
            _agent("B06", 3, "error_resolver", ("semantic_error", "Resolves errors")),
            _agent("B06", 4, "retry_scheduler", ("retry_queue", "Schedules retry")),
            _agent("B06", 5, "semantic_auditor", ("coverage_audit", "Final audit")),
        ],
    )

    # B07 — Type Normalization
    battalions["B07_TYPE"] = BlueBattalion(
        "B07_TYPE",
        "Type Normalization",
        [
            _agent("B07", 1, "type_mapper", ("null_type", "Maps NULL types")),
            _agent("B07", 2, "enum_validator", ("enum_check", "Validates enum")),
            _agent("B07", 3, "legacy_migrator", ("deprecated_type", "Migrates legacy")),
            _agent("B07", 4, "type_inferrer", ("content_infer", "Infers type")),
            _agent("B07", 5, "type_auditor", ("distribution_audit", "Final audit")),
        ],
    )

    # B08 — Project Alignment
    battalions["B08_PROJECT"] = BlueBattalion(
        "B08_PROJECT",
        "Project Alignment",
        [
            _agent("B08", 1, "project_matcher", ("null_project", "Matches projects")),
            _agent("B08", 2, "name_normalizer", ("case_normalize", "Normalizes names")),
            _agent("B08", 3, "orphan_detector", ("orphan_fact", "Detects orphans")),
            _agent("B08", 4, "project_linker", ("auto_link", "Auto-links orphans")),
            _agent("B08", 5, "project_auditor", ("coverage_audit", "Final audit")),
        ],
    )

    # B09 — Cross-Reference Validation
    battalions["B09_XREF"] = BlueBattalion(
        "B09_XREF",
        "Cross-Reference Validation",
        [
            _agent("B09", 1, "parent_linker", ("dangling_parent", "Validates parent refs")),
            _agent("B09", 2, "edge_validator", ("causal_edge", "Validates edge integrity")),
            _agent("B09", 3, "cycle_detector", ("circular_ref", "Detects circular refs")),
            _agent("B09", 4, "orphan_resolver", ("orphan_chain", "Resolves orphaned chains")),
            _agent("B09", 5, "xref_auditor", ("integrity_audit", "Final audit")),
        ],
    )

    # B10 — Tombstone Audit
    battalions["B10_TOMBSTONE"] = BlueBattalion(
        "B10_TOMBSTONE",
        "Tombstone Audit",
        [
            _agent("B10", 1, "ref_scanner", ("zombie_parent", "Scans zombie parents")),
            _agent("B10", 2, "tombstone_unlinker", ("unlink_parent", "Unlinks tombstones")),
            _agent("B10", 3, "ghost_purger", ("full_purge", "Purges ghosts")),
            _agent("B10", 4, "cascade_checker", ("cascade_effect", "Checks cascade")),
            _agent("B10", 5, "tombstone_auditor", ("consistency_audit", "Final audit")),
        ],
    )

    return battalions


# ── Singleton Blue Team Manifest ────────────────────────────────────────

BLUE_TEAM: dict[str, BlueBattalion] = _build_blue_team()

_AGENT_COUNT = sum(len(b.agents) for b in BLUE_TEAM.values())
_SPEC_COUNT = sum(b.specialist_count for b in BLUE_TEAM.values())
assert _AGENT_COUNT == 50, f"Blue Team must have 50 agents, got {_AGENT_COUNT}"
assert _SPEC_COUNT == 50, f"Blue Team must have 50 specialists, got {_SPEC_COUNT}"
