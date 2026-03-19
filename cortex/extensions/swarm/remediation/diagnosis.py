"""LEGION-Ω Diagnosis Classifier — Deterministic Gap Scanner.

Scans the facts table and categorizes each pending fact into a battalion
assignment based on structural defects (NULL hash, invalid confidence, etc.).
Zero LLM — pure SQL + Python determinism.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

import aiosqlite

from cortex.database.core import connect_async_ctx

logger = logging.getLogger("cortex.swarm.remediation.diagnosis")

# Valid fact_type values per CORTEX schema
VALID_FACT_TYPES = frozenset(
    {
        "observation",
        "decision",
        "axiom",
        "pattern",
        "crystal",
        "ghost",
        "scar",
        "architecture",
        "workflow",
        "rule",
        "insight",
        "warning",
        "note",
        "identity",
        "knowledge",
    }
)

# Valid semantic_status values
VALID_SEMANTIC_STATUSES = frozenset({"pending", "processing", "completed", "error", "skipped"})

# Mapping of legacy/deprecated types to canonical CORTEX types
LEGACY_TYPE_MAP = {
    "system_bridge": "architecture",
    "bridge": "architecture",
    "code_ghost": "ghost",
    "fact": "observation",
    "task": "workflow",
    "memory": "pattern",
    "thought": "insight",
    "error": "warning",
    "log": "note",
    "issue": "warning",
}


@dataclass(frozen=True)
class Diagnosis:
    """A single diagnosed defect in a fact."""

    fact_id: str
    battalion: str
    issue: str
    severity: str  # P0, P1, P2
    description: str
    fix_sql: str | None = None
    fix_params: tuple[Any, ...] = ()

    @property
    def is_critical(self) -> bool:
        return self.severity == "P0"


class DiagnosisClassifier:
    """Scans facts and classifies defects into battalion assignments.

    Each diagnostic rule is a pure function: fact_row → Diagnosis | None.
    Rules are applied in priority order (P0 first).
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def scan_all(self) -> list[Diagnosis]:
        """Full-table diagnostic scan. Returns all diagnosed issues."""
        diagnoses: list[Diagnosis] = []

        async with connect_async_ctx(self._db_path, read_only=True) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, content, fact_type, hash, confidence, exergy_score, "
                "source, semantic_status, project, parent_id, is_tombstoned, "
                "metadata, quadrant, storage_tier, category "
                "FROM facts WHERE is_tombstoned = 0 OR is_tombstoned IS NULL"
            )
            rows = await cursor.fetchall()

            # Also fetch all valid fact IDs for cross-reference checks
            id_cursor = await db.execute("SELECT id FROM facts")
            all_ids = {row[0] for row in await id_cursor.fetchall()}

            # Fetch tombstoned IDs referenced as parents
            tomb_cursor = await db.execute(
                "SELECT DISTINCT f1.id FROM facts f1 "
                "INNER JOIN facts f2 ON f2.parent_id = f1.id "
                "WHERE f1.is_tombstoned = 1 AND (f2.is_tombstoned = 0 OR f2.is_tombstoned IS NULL)"
            )
            zombie_parents = {row[0] for row in await tomb_cursor.fetchall()}

        for row in rows:
            fact = dict(row)
            fact_id = fact["id"]

            # B01 — Schema Integrity
            if fact["content"] is None or str(fact["content"]).strip() == "":
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B01_SCHEMA",
                        issue="EMPTY_CONTENT",
                        severity="P0",
                        description="Fact has empty or NULL content — unverifiable.",
                    )
                )

            # B02 — Hash Reconstruction
            if fact["hash"] is None or str(fact["hash"]).strip() == "":
                expected = hashlib.sha256(str(fact.get("content", "")).encode()).hexdigest()
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B02_HASH",
                        issue="NULL_HASH",
                        severity="P0",
                        description="Fact is missing its SHA-256 hash — chain trust broken.",
                        fix_sql="UPDATE facts SET hash = ? WHERE id = ?",
                        fix_params=(expected, fact_id),
                    )
                )
            elif fact["content"] is not None:
                expected = hashlib.sha256(str(fact["content"]).encode()).hexdigest()
                if fact["hash"] != expected:
                    diagnoses.append(
                        Diagnosis(
                            fact_id=fact_id,
                            battalion="B02_HASH",
                            issue="HASH_MISMATCH",
                            severity="P0",
                            description=(
                                f"Hash mismatch: stored={fact['hash'][:12]}… "
                                f"expected={expected[:12]}…"
                            ),
                            fix_sql="UPDATE facts SET hash = ? WHERE id = ?",
                            fix_params=(expected, fact_id),
                        )
                    )

            # B03 — Confidence Calibration
            conf = fact["confidence"]
            try:
                conf_val = float(conf) if conf is not None else None
            except (ValueError, TypeError):
                # Map epistemic codes (C1-C5) to float values
                conf_str = str(conf).upper()
                if "C5" in conf_str:
                    conf_val = 1.0
                elif "C4" in conf_str:
                    conf_val = 0.8
                elif "C3" in conf_str:
                    conf_val = 0.6
                elif "C2" in conf_str:
                    conf_val = 0.4
                elif "C1" in conf_str:
                    conf_val = 0.2
                else:
                    conf_val = -1.0  # Mark for remediation

            if conf_val is None:
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B03_CONFIDENCE",
                        issue="NULL_CONFIDENCE",
                        severity="P1",
                        description="Confidence is NULL — defaulting to 0.5.",
                        fix_sql="UPDATE facts SET confidence = 0.5 WHERE id = ?",
                        fix_params=(fact_id,),
                    )
                )
            elif not (0.0 <= conf_val <= 1.0):
                clamped = max(0.0, min(1.0, conf_val)) if conf_val != -1.0 else 0.5
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B03_CONFIDENCE",
                        issue="CONFIDENCE_OUT_OF_BOUNDS",
                        severity="P1",
                        description=f"Confidence {conf} outside [0,1] — clamping to {clamped}.",
                        fix_sql="UPDATE facts SET confidence = ? WHERE id = ?",
                        fix_params=(clamped, fact_id),
                    )
                )

            # B04 — Exergy Scoring
            exergy = fact["exergy_score"]
            try:
                exergy_val = float(exergy) if exergy is not None else None
            except (ValueError, TypeError):
                exergy_val = None
            if exergy_val is None or exergy_val == 0.0:
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B04_EXERGY",
                        issue="MISSING_EXERGY",
                        severity="P2",
                        description="Exergy score is NULL or zero — needs recalculation.",
                    )
                )

            # B05 — Source Attribution
            src = fact["source"]
            if src is None or str(src).strip() == "":
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B05_SOURCE",
                        issue="MISSING_SOURCE",
                        severity="P1",
                        description="Source attribution is missing.",
                        fix_sql="UPDATE facts SET source = 'unknown' WHERE id = ?",
                        fix_params=(fact_id,),
                    )
                )

            # B06 — Semantic Enrichment
            sem = fact["semantic_status"]
            if sem is not None and sem not in VALID_SEMANTIC_STATUSES:
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B06_SEMANTIC",
                        issue="INVALID_SEMANTIC_STATUS",
                        severity="P1",
                        description=f"Semantic status '{sem}' is not a valid enum value.",
                        fix_sql="UPDATE facts SET semantic_status = 'pending' WHERE id = ?",
                        fix_params=(fact_id,),
                    )
                )
            elif sem in ("error", "pending"):
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B06_SEMANTIC",
                        issue="ENRICHMENT_INCOMPLETE",
                        severity="P2",
                        description=f"Semantic status is '{sem}' — needs re-enrichment.",
                    )
                )

            # B07 — Type Normalization
            ft = fact["fact_type"]
            if ft is None or str(ft).strip() == "":
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B07_TYPE",
                        issue="NULL_TYPE",
                        severity="P1",
                        description="Fact type is NULL — defaulting to 'observation'.",
                        fix_sql="UPDATE facts SET fact_type = 'observation' WHERE id = ?",
                        fix_params=(fact_id,),
                    )
                )
            elif str(ft) not in VALID_FACT_TYPES:
                canonical = LEGACY_TYPE_MAP.get(str(ft))
                fix_sql = "UPDATE facts SET fact_type = ? WHERE id = ?" if canonical else None
                fix_params = (canonical, fact_id) if canonical else ()

                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B07_TYPE",
                        issue="INVALID_TYPE",
                        severity="P1",
                        description=f"Fact type '{ft}' not in valid enum.",
                        fix_sql=fix_sql,
                        fix_params=fix_params,
                    )
                )

            # B08 — Project Alignment
            proj = fact["project"]
            if proj is None or str(proj).strip() == "":
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B08_PROJECT",
                        issue="NULL_PROJECT",
                        severity="P2",
                        description="Project is NULL — orphaned fact.",
                    )
                )

            # B09 — Cross-Reference Validation
            pid = fact["parent_id"]
            if pid is not None and pid not in all_ids:
                diagnoses.append(
                    Diagnosis(
                        fact_id=fact_id,
                        battalion="B09_XREF",
                        issue="DANGLING_PARENT",
                        severity="P1",
                        description=f"parent_id '{pid}' references non-existent fact.",
                        fix_sql="UPDATE facts SET parent_id = NULL WHERE id = ?",
                        fix_params=(fact_id,),
                    )
                )

        # B10 — Tombstone Audit (separate pass)
        for zombie_id in zombie_parents:
            diagnoses.append(
                Diagnosis(
                    fact_id=zombie_id,
                    battalion="B10_TOMBSTONE",
                    issue="ZOMBIE_PARENT",
                    severity="P1",
                    description="Tombstoned fact is still referenced as parent by active facts.",
                )
            )

        logger.info(
            "Diagnosis complete: %d issues across %d facts",
            len(diagnoses),
            len(rows),
        )
        return diagnoses

    async def scan_battalion(self, battalion: str) -> list[Diagnosis]:
        """Return diagnoses filtered to a specific battalion."""
        all_diag = await self.scan_all()
        return [d for d in all_diag if d.battalion == battalion]

    async def summary(self) -> dict[str, int]:
        """Return count of issues per battalion."""
        all_diag = await self.scan_all()
        counts: dict[str, int] = {}
        for d in all_diag:
            counts[d.battalion] = counts.get(d.battalion, 0) + 1
        return counts
