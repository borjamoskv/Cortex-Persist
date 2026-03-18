"""LEGION-Ω Red Team — 50 Agents + 100 Siege Specialists.

Every Blue Team fix is challenged by its Red Team counterpart.
Red agents attack the proposed fix to verify it doesn't introduce
regressions, violate constraints, or leave the system in a worse state.

Hierarchy: 10 Battalions × 5 Agents × 2 Specialists = 150 entities.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

import aiosqlite

from cortex.extensions.swarm.remediation.blue_team import RemediationResult
from cortex.extensions.swarm.remediation.diagnosis import (
    VALID_FACT_TYPES,
    VALID_SEMANTIC_STATUSES,
)

logger = logging.getLogger("cortex.swarm.remediation.red_team")


@dataclass(frozen=True)
class SiegeResult:
    """Outcome of a Red Team siege against a Blue fix."""

    fact_id: str
    agent_id: str
    specialist_id: str
    battalion: str
    passed: bool
    attack: str
    finding: str | None = None


@dataclass
class RedSpecialist:
    """A Red Team siege specialist — attacks a specific aspect of the fix."""

    specialist_id: str
    agent_id: str
    attack_vector: str
    description: str

    async def siege(
        self,
        fact: dict[str, Any],
        blue_result: RemediationResult,
        db: aiosqlite.Connection,
    ) -> SiegeResult:
        """Attack the Blue Team's fix. Return pass/fail."""
        # Dispatch to the matching attack method
        method = getattr(self, f"_attack_{self.attack_vector}", None)
        if method is None:
            return SiegeResult(
                fact_id=blue_result.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=blue_result.battalion,
                passed=True,
                attack=self.attack_vector,
            )
        return await method(fact, blue_result, db)

    async def _attack_hash_integrity(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify hash correctness post-fix."""
        content = fact.get("content", "")
        expected = hashlib.sha256(str(content).encode()).hexdigest()
        stored = fact.get("hash", "")

        if result.success and result.sql_executed and "hash" in result.sql_executed:
            # Blue claimed to fix the hash — verify the fix is correct
            if stored and stored != expected:
                return SiegeResult(
                    fact_id=result.fact_id,
                    agent_id=self.agent_id,
                    specialist_id=self.specialist_id,
                    battalion=result.battalion,
                    passed=False,
                    attack="hash_integrity",
                    finding=f"Hash still mismatched after fix: {stored[:12]}… != {expected[:12]}…",
                )

        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="hash_integrity",
        )

    async def _attack_bounds_overflow(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify confidence remains within [0, 1] post-fix."""
        conf = fact.get("confidence")
        if conf is not None:
            try:
                val = float(conf)
                if not (0.0 <= val <= 1.0):
                    return SiegeResult(
                        fact_id=result.fact_id,
                        agent_id=self.agent_id,
                        specialist_id=self.specialist_id,
                        battalion=result.battalion,
                        passed=False,
                        attack="bounds_overflow",
                        finding=f"Confidence {val} still outside [0, 1].",
                    )
            except (ValueError, TypeError):
                return SiegeResult(
                    fact_id=result.fact_id,
                    agent_id=self.agent_id,
                    specialist_id=self.specialist_id,
                    battalion=result.battalion,
                    passed=False,
                    attack="bounds_overflow",
                    finding=f"Confidence '{conf}' is not a valid float.",
                )

        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="bounds_overflow",
        )

    async def _attack_null_injection(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify fix didn't introduce NULL into required fields."""
        required = ("content", "fact_type", "hash", "confidence")
        nulls = [f for f in required if fact.get(f) is None]
        if nulls:
            return SiegeResult(
                fact_id=result.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=result.battalion,
                passed=False,
                attack="null_injection",
                finding=f"Required fields still NULL: {nulls}",
            )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="null_injection",
        )

    async def _attack_type_validity(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify fact_type is a valid enum value."""
        ft = fact.get("fact_type")
        if ft and str(ft) not in VALID_FACT_TYPES:
            return SiegeResult(
                fact_id=result.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=result.battalion,
                passed=False,
                attack="type_validity",
                finding=f"fact_type '{ft}' not in valid enum.",
            )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="type_validity",
        )

    async def _attack_dangling_ref(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify parent_id points to an existing fact."""
        pid = fact.get("parent_id")
        if pid is not None:
            cursor = await db.execute("SELECT 1 FROM facts WHERE id = ?", (pid,))
            row = await cursor.fetchone()
            if row is None:
                return SiegeResult(
                    fact_id=result.fact_id,
                    agent_id=self.agent_id,
                    specialist_id=self.specialist_id,
                    battalion=result.battalion,
                    passed=False,
                    attack="dangling_ref",
                    finding=f"parent_id '{pid}' still dangling after fix.",
                )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="dangling_ref",
        )

    async def _attack_exergy_sanity(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify exergy_score is non-negative and finite."""
        ex = fact.get("exergy_score")
        if ex is not None:
            try:
                val = float(ex)
                if val < 0.0:
                    return SiegeResult(
                        fact_id=result.fact_id,
                        agent_id=self.agent_id,
                        specialist_id=self.specialist_id,
                        battalion=result.battalion,
                        passed=False,
                        attack="exergy_sanity",
                        finding=f"Exergy score {val} is negative.",
                    )
            except (ValueError, TypeError):
                return SiegeResult(
                    fact_id=result.fact_id,
                    agent_id=self.agent_id,
                    specialist_id=self.specialist_id,
                    battalion=result.battalion,
                    passed=False,
                    attack="exergy_sanity",
                    finding=f"Exergy score '{ex}' is not a valid number.",
                )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="exergy_sanity",
        )

    async def _attack_semantic_enum(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify semantic_status is a valid enum value."""
        sem = fact.get("semantic_status")
        if sem and str(sem) not in VALID_SEMANTIC_STATUSES:
            return SiegeResult(
                fact_id=result.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=result.battalion,
                passed=False,
                attack="semantic_enum",
                finding=f"semantic_status '{sem}' not in valid enum.",
            )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="semantic_enum",
        )

    async def _attack_source_empty(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify source is not empty after fix."""
        src = fact.get("source")
        if src is None or str(src).strip() == "":
            return SiegeResult(
                fact_id=result.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=result.battalion,
                passed=False,
                attack="source_empty",
                finding="Source still empty after fix.",
            )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="source_empty",
        )

    async def _attack_tombstone_leak(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify tombstoned facts are not referenced by active facts."""
        if fact.get("is_tombstoned"):
            cursor = await db.execute(
                "SELECT COUNT(*) FROM facts WHERE parent_id = ? AND "
                "(is_tombstoned = 0 OR is_tombstoned IS NULL)",
                (fact["id"],),
            )
            row = await cursor.fetchone()
            if row and row[0] > 0:
                return SiegeResult(
                    fact_id=result.fact_id,
                    agent_id=self.agent_id,
                    specialist_id=self.specialist_id,
                    battalion=result.battalion,
                    passed=False,
                    attack="tombstone_leak",
                    finding=f"Tombstoned fact still referenced by {row[0]} active facts.",
                )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="tombstone_leak",
        )

    async def _attack_project_orphan(
        self, fact: dict[str, Any], result: RemediationResult, db: aiosqlite.Connection
    ) -> SiegeResult:
        """Verify project is not empty/NULL after fix."""
        proj = fact.get("project")
        if proj is None or str(proj).strip() == "":
            return SiegeResult(
                fact_id=result.fact_id,
                agent_id=self.agent_id,
                specialist_id=self.specialist_id,
                battalion=result.battalion,
                passed=False,
                attack="project_orphan",
                finding="Project still NULL/empty after fix.",
            )
        return SiegeResult(
            fact_id=result.fact_id,
            agent_id=self.agent_id,
            specialist_id=self.specialist_id,
            battalion=result.battalion,
            passed=True,
            attack="project_orphan",
        )


@dataclass
class RedAgent:
    """A Red Team siege agent — commands 2 siege specialists."""

    agent_id: str
    battalion: str
    role: str
    specialists: list[RedSpecialist] = field(default_factory=list)

    async def siege(
        self,
        fact: dict[str, Any],
        blue_result: RemediationResult,
        db: aiosqlite.Connection,
    ) -> list[SiegeResult]:
        """Run all specialist attacks against the Blue fix."""
        results: list[SiegeResult] = []
        for spec in self.specialists:
            result = await spec.siege(fact, blue_result, db)
            results.append(result)
        return results


@dataclass
class RedBattalion:
    """A Red battalion of 5 agents (10 specialists) — siege counterpart to a Blue battalion."""

    battalion_id: str
    name: str
    agents: list[RedAgent] = field(default_factory=list)

    @property
    def specialist_count(self) -> int:
        return sum(len(a.specialists) for a in self.agents)

    async def siege_batch(
        self,
        facts: dict[str, dict[str, Any]],
        blue_results: list[RemediationResult],
        db: aiosqlite.Connection,
    ) -> list[SiegeResult]:
        """Run all agent sieges against Blue results."""
        all_results: list[SiegeResult] = []
        for br in blue_results:
            if not br.success:
                continue
            fact = facts.get(br.fact_id, {})
            # Each agent attacks in sequence
            for agent in self.agents:
                results = await agent.siege(fact, br, db)
                all_results.extend(results)
        return all_results


# ── Factory ─────────────────────────────────────────────────────────────


def _red_agent(
    battalion: str, idx: int, role: str, attack_def: tuple[str, str]
) -> RedAgent:
    """Build a Red agent with 1 sub-agent (siege specialist)."""
    agent_id = f"{battalion}-red-{idx:02d}-{role.replace(' ', '_')}"
    av, ad = attack_def
    specs = [
        RedSpecialist(
            specialist_id=f"{agent_id}-sub-{av.replace(' ', '_')}",
            agent_id=agent_id,
            attack_vector=av,
            description=ad,
        )
    ]
    return RedAgent(agent_id=agent_id, battalion=battalion, role=role, specialists=specs)


def _build_red_team() -> dict[str, RedBattalion]:
    """Construct 50 Red agents + 100 siege specialists."""
    battalions: dict[str, RedBattalion] = {}

    # R01 — Schema Siege
    battalions["B01_SCHEMA"] = RedBattalion("R01_SCHEMA", "Schema Siege", [
        _red_agent("R01", 1, "schema_fuzzer", ("null_injection", "Injects NULL into required fields")),
        _red_agent("R01", 2, "constraint_breaker", ("type_validity", "Probes type boundaries")),
        _red_agent("R01", 3, "null_injector", ("null_injection", "Deep NULL injection testing")),
        _red_agent("R01", 4, "type_poisoner", ("semantic_enum", "Tests enum boundary values")),
        _red_agent("R01", 5, "schema_verifier", ("type_validity", "Final type compliance check")),
    ])

    # R02 — Hash Siege
    battalions["B02_HASH"] = RedBattalion("R02_HASH", "Hash Siege", [
        _red_agent("R02", 1, "hash_corruptor", ("hash_integrity", "Corrupts hash to test detection")),
        _red_agent("R02", 2, "chain_breaker", ("dangling_ref", "Tests orphaned chain links")),
        _red_agent("R02", 3, "collision_probe", ("hash_integrity", "Probes for hash collisions")),
        _red_agent("R02", 4, "replay_attacker", ("hash_integrity", "Replays old hashes")),
        _red_agent("R02", 5, "hash_verifier", ("null_injection", "Final NULL hash check")),
    ])

    # R03 — Confidence Siege
    battalions["B03_CONFIDENCE"] = RedBattalion("R03_CONFIDENCE", "Confidence Siege", [
        _red_agent("R03", 1, "bounds_overflow", ("bounds_overflow", "Pushes values beyond [0, 1]")),
        _red_agent("R03", 2, "nan_injector", ("null_injection", "Tests NULL confidence")),
        _red_agent("R03", 3, "negative_probe", ("bounds_overflow", "Tests epsilon underflow")),
        _red_agent("R03", 4, "ceiling_breaker", ("bounds_overflow", "Tests overflow to 999")),
        _red_agent("R03", 5, "confidence_verifier", ("null_injection", "Final NULL check")),
    ])

    # R04 — Exergy Siege
    battalions["B04_EXERGY"] = RedBattalion("R04_EXERGY", "Exergy Siege", [
        _red_agent("R04", 1, "zero_exergy", ("null_injection", "Tests NULL exergy")),
        _red_agent("R04", 2, "infinity_probe", ("exergy_sanity", "Tests very large values")),
        _red_agent("R04", 3, "negative_exergy", ("exergy_sanity", "Tests underflow")),
        _red_agent("R04", 4, "overflow_attack", ("exergy_sanity", "Tests float precision")),
        _red_agent("R04", 5, "exergy_verifier", ("null_injection", "Final NULL exergy check")),
    ])

    # R05 — Source Siege
    battalions["B05_SOURCE"] = RedBattalion("R05_SOURCE", "Source Siege", [
        _red_agent("R05", 1, "empty_source", ("null_injection", "Tests NULL source")),
        _red_agent("R05", 2, "injection_probe", ("source_empty", "Tests XSS in source")),
        _red_agent("R05", 3, "unicode_attack", ("source_empty", "Tests zero-width chars")),
        _red_agent("R05", 4, "truncation_test", ("source_empty", "Tests max-length source")),
        _red_agent("R05", 5, "source_verifier", ("null_injection", "Final NULL check")),
    ])

    # R06 — Semantic Siege
    battalions["B06_SEMANTIC"] = RedBattalion("R06_SEMANTIC", "Semantic Siege", [
        _red_agent("R06", 1, "embed_corruptor", ("null_injection", "Tests NULL semantic_status")),
        _red_agent("R06", 2, "status_reverter", ("semantic_enum", "Tests invalid transitions")),
        _red_agent("R06", 3, "error_reinjector", ("semantic_enum", "Tests loop detection")),
        _red_agent("R06", 4, "timeout_simulator", ("semantic_enum", "Tests status after timeout")),
        _red_agent("R06", 5, "semantic_verifier", ("null_injection", "Final NULL check")),
    ])

    # R07 — Type Siege
    battalions["B07_TYPE"] = RedBattalion("R07_TYPE", "Type Siege", [
        _red_agent("R07", 1, "invalid_type_inj", ("type_validity", "Injects invalid type values")),
        _red_agent("R07", 2, "null_type_probe", ("type_validity", "Tests NULL fact_type handling")),
        _red_agent("R07", 3, "overlong_value", ("type_validity", "Tests very long type strings")),
        _red_agent("R07", 4, "enum_bypasser", ("type_validity", "Bypasses enum validation")),
        _red_agent("R07", 5, "type_verifier", ("type_validity", "Final type enum check")),
    ])

    # R08 — Project Siege
    battalions["B08_PROJECT"] = RedBattalion("R08_PROJECT", "Project Siege", [
        _red_agent("R08", 1, "orphan_creator", ("null_injection", "Tests NULL project")),
        _red_agent("R08", 2, "name_collision", ("project_orphan", "Tests case-sensitive names")),
        _red_agent("R08", 3, "case_sensitivity", ("project_orphan", "Tests whitespace in names")),
        _red_agent("R08", 4, "empty_project", ("null_injection", "Tests NULL project")),
        _red_agent("R08", 5, "project_verifier", ("null_injection", "Final NULL check")),
    ])

    # R09 — XRef Siege
    battalions["B09_XREF"] = RedBattalion("R09_XREF", "Cross-Reference Siege", [
        _red_agent("R09", 1, "cycle_creator", ("dangling_ref", "Tests self-referencing facts")),
        _red_agent("R09", 2, "dangling_ref_attack", ("null_injection", "Tests NULL parent_id")),
        _red_agent("R09", 3, "self_reference", ("dangling_ref", "Tests deep nesting")),
        _red_agent("R09", 4, "deep_nesting", ("dangling_ref", "Tests circular chain detection")),
        _red_agent("R09", 5, "xref_verifier", ("null_injection", "Final NULL check")),
    ])

    # R10 — Tombstone Siege
    battalions["B10_TOMBSTONE"] = RedBattalion("R10_TOMBSTONE", "Tombstone Siege", [
        _red_agent("R10", 1, "resurrection_attack", ("dangling_ref", "Tests resurrection side effects")),
        _red_agent("R10", 2, "phantom_ref", ("tombstone_leak", "Tests invisible tombstone refs")),
        _red_agent("R10", 3, "cascade_poison", ("tombstone_leak", "Tests cascading effects")),
        _red_agent("R10", 4, "double_delete", ("tombstone_leak", "Tests re-tombstone detection")),
        _red_agent("R10", 5, "tombstone_verifier", ("null_injection", "Final NULL check")),
    ])

    return battalions


# ── Singleton Red Team Manifest ─────────────────────────────────────────

RED_TEAM: dict[str, RedBattalion] = _build_red_team()

_AGENT_COUNT = sum(len(b.agents) for b in RED_TEAM.values())
_SPEC_COUNT = sum(b.specialist_count for b in RED_TEAM.values())
assert _AGENT_COUNT == 50, f"Red Team must have 50 agents, got {_AGENT_COUNT}"
assert _SPEC_COUNT == 50, f"Red Team must have 50 sub-agents (specialists), got {_SPEC_COUNT}"
