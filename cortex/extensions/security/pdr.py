"""Policy Decision Record (PDR) — CORTEX Implementation.

Aligned with arXiv:2601.04583v1 §8.3 Policy Decision Record.
Provides verifiable, auditable proof of policy compliance for
agent-mediated actions in the CORTEX pipeline.

This module defines the PDR dataclass and workflow. Every
CORTEX-GUARD evaluation SHOULD produce a PDR record alongside
its pass/fail determination.

Reference: Appendix B — PDR Reference Implementation (JWT Profile).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class PDRDecision(Enum):
    """Policy decision outcomes per §8.3."""
    PERMIT = "PERMIT"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass
class PolicyEvaluation:
    """Single policy rule evaluation result."""
    rule_id: str
    rule_name: str
    result: bool
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "result": self.result,
            "evidence": self.evidence,
        }


@dataclass
class PolicyDecisionRecord:
    """PDR Core Schema — verifiable proof of compliance.

    Attributes:
        decision_id: Unique identifier for this decision.
        tis_hash: SHA-256 hash of the canonical TIS being evaluated.
        policy_id: Identifier of the policy set applied.
        decision: PERMIT | DENY | ESCALATE.
        evaluations: Individual rule evaluation results.
        signer: Key/agent identifier that produced the decision.
        timestamp: ISO8601 evaluation timestamp.
        conformance_level: L0-L3 per Appendix C.
        metadata: Additional context.
    """

    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tis_hash: str = ""
    policy_id: str = "cortex-guard-omega"
    decision: PDRDecision = PDRDecision.DENY
    evaluations: list[PolicyEvaluation] = field(default_factory=list)
    signer: str = "cortex-guard"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    conformance_level: str = "L1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_evaluation(
        self,
        rule_id: str,
        rule_name: str,
        result: bool,
        evidence: str = "",
    ) -> None:
        """Add a policy evaluation to this PDR."""
        self.evaluations.append(
            PolicyEvaluation(
                rule_id=rule_id,
                rule_name=rule_name,
                result=result,
                evidence=evidence,
            )
        )

    def compute_decision(self) -> PDRDecision:
        """Compute aggregate decision from evaluations.

        All rules must pass for PERMIT. Any failure = DENY.
        If no evaluations exist, ESCALATE (insufficient evidence).
        """
        if not self.evaluations:
            self.decision = PDRDecision.ESCALATE
            return self.decision

        all_pass = all(e.result for e in self.evaluations)
        self.decision = PDRDecision.PERMIT if all_pass else PDRDecision.DENY
        return self.decision

    def canonical_hash(self) -> str:
        """Compute SHA-256 of canonical PDR representation."""
        data = self.to_dict()
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Export PDR as dictionary for JSON/JSONL serialization."""
        return {
            "decision_id": self.decision_id,
            "tis_hash": self.tis_hash,
            "policy_id": self.policy_id,
            "decision": self.decision.value,
            "evaluations": [e.to_dict() for e in self.evaluations],
            "signer": self.signer,
            "timestamp": self.timestamp,
            "conformance_level": self.conformance_level,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export PDR as formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_guard_result(
        cls,
        tis_hash: str,
        gate_results: dict[str, tuple[bool, str]],
        conformance_level: str = "L1",
    ) -> "PolicyDecisionRecord":
        """Construct PDR from CORTEX-GUARD gate evaluation results.

        Maps the existing guard gate system (check_gate_X) to
        PDR-compatible evaluation records.

        Args:
            tis_hash: Canonical hash of the TIS being evaluated.
            gate_results: Dict of {gate_name: (passed, evidence)}.
            conformance_level: Current conformance target (L0-L3).
        """
        pdr = cls(
            tis_hash=tis_hash,
            conformance_level=conformance_level,
        )

        for gate_name, (passed, evidence) in gate_results.items():
            pdr.add_evaluation(
                rule_id=gate_name,
                rule_name=gate_name.replace("_", " ").title(),
                result=passed,
                evidence=evidence,
            )

        pdr.compute_decision()
        return pdr
