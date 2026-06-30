from decimal import Decimal
# [C5-REAL] Exergy-Maximized
"""SICA Constitution - Immutable Epistemic Principles.

Inspired by Anthropic Constitutional AI. Every agent output is evaluated
against a set of principles BEFORE emission. Violations trigger meta-level
intervention (strategy mutation, output revision, or task abort).

Principles are organized by severity:
  - CARDINAL: violation = immediate abort + quarantine
  - STRUCTURAL: violation = output revision + meta-log
  - ADVISORY: violation = meta-log only (soft feedback)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("babylon60.sica.constitution")


class Severity(str, Enum):
    """Principle violation severity."""

    CARDINAL = "cardinal"  # Abort + quarantine
    STRUCTURAL = "structural"  # Revise output + log
    ADVISORY = "advisory"  # Log only


@dataclass(frozen=True)
class Principle:
    """A single constitutional principle.

    Attributes:
        id: Unique identifier (e.g., "P001-TRUTH").
        name: Human-readable name.
        description: Full statement of the principle.
        severity: Consequence class on violation.
        evaluator: Callable or evaluation key for automated checking.
    """

    id: str
    name: str
    description: str
    severity: Severity
    evaluator: str = ""  # Strategy key for meta-level evaluation

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.id}: {self.name}"


@dataclass
class Violation:
    """Record of a constitutional violation."""

    principle: Principle
    context: str
    explanation: str
    timestamp: float = field(default_factory=time.monotonic)
    resolved: bool = False
    resolution: str = ""


@dataclass
class ConstitutionalVerdict:
    """Result of evaluating an output against the constitution."""

    passed: bool
    violations: list[Violation] = field(default_factory=list)
    score: Decimal = 1.0  # 1.0 = perfect compliance, 0.0 = full violation
    revision_needed: bool = False
    abort_needed: bool = False

    @property
    def cardinal_violations(self) -> list[Violation]:
        return [v for v in self.violations if v.principle.severity == Severity.CARDINAL]

    @property
    def structural_violations(self) -> list[Violation]:
        return [v for v in self.violations if v.principle.severity == Severity.STRUCTURAL]


class Constitution:
    """The agent's constitutional framework.

    Holds an immutable set of principles against which every output
    is evaluated before emission. The constitution itself CANNOT be
    modified at runtime - only the strategies for complying with it
    can evolve.
    """

    # ── Default CORTEX Principles ────────────────────────────────

    DEFAULT_PRINCIPLES = (
        Principle(
            id="P001-TRUTH",
            name="Reality Level Declaration",
            description=(
                "Every state mutation, claim, or output MUST declare its reality level: "
                "C5-REAL (verifiable) or C4-SIM (simulated). Presenting simulation as "
                "verifiable proof is a cardinal violation."
            ),
            severity=Severity.CARDINAL,
            evaluator="reality_level_check",
        ),
        Principle(
            id="P002-FALSIFIABILITY",
            name="Falsifiable Claims",
            description=(
                "Every factual claim must include sufficient context for falsification. "
                "Unfalsifiable assertions are structurally deficient."
            ),
            severity=Severity.STRUCTURAL,
            evaluator="falsifiability_check",
        ),
        Principle(
            id="P003-EXERGY",
            name="Exergy Maximization",
            description=(
                "Every action must increase available useful work (exergy) in the system. "
                "Entropy-only operations without compensating exergy are advisory violations."
            ),
            severity=Severity.ADVISORY,
            evaluator="exergy_check",
        ),
        Principle(
            id="P004-IDEMPOTENCY",
            name="Safe Retry Guarantee",
            description=(
                "Operations that modify external state must be idempotent or explicitly "
                "declare non-idempotency with rollback strategy."
            ),
            severity=Severity.STRUCTURAL,
            evaluator="idempotency_check",
        ),
        Principle(
            id="P005-METACOGNITIVE-HONESTY",
            name="Metacognitive Honesty",
            description=(
                "The agent must accurately represent its confidence level and reasoning "
                "process. Fabricating reasoning chains is a cardinal violation."
            ),
            severity=Severity.CARDINAL,
            evaluator="metacognitive_honesty_check",
        ),
        Principle(
            id="P006-PROTECTED-PATHS",
            name="Protected Path Sovereignty",
            description=(
                "Never touch protected filesystem paths, CloudDocs, or system assets. "
                "Violations are cardinal - data loss is irreversible."
            ),
            severity=Severity.CARDINAL,
            evaluator="protected_paths_check",
        ),
    )

    def __init__(
        self,
        principles: tuple[Principle, ...] | None = None,
    ) -> None:
        self._principles: tuple[Principle, ...] = principles or self.DEFAULT_PRINCIPLES
        self._violation_history: list[Violation] = []

    @property
    def principles(self) -> tuple[Principle, ...]:
        return self._principles

    @property
    def violation_history(self) -> list[Violation]:
        return list(self._violation_history)

    def evaluate(
        self,
        output: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ConstitutionalVerdict:
        """Evaluate an output against all constitutional principles.

        This is a structural evaluation - concrete evaluator implementations
        are plugged in via the meta-level's evaluation registry.
        """
        violations: list[Violation] = []
        ctx = context or {}

        for principle in self._principles:
            # Structural checks that can be done without LLM
            violation = self._structural_check(principle, output, ctx)
            if violation is not None:
                violations.append(violation)
                self._violation_history.append(violation)

        abort = any(v.principle.severity == Severity.CARDINAL for v in violations)
        revision = any(v.principle.severity == Severity.STRUCTURAL for v in violations)

        total = len(self._principles)
        violated = len(violations)
        score = (total - violated) / total if total > 0 else 1.0

        verdict = ConstitutionalVerdict(
            passed=len(violations) == 0,
            violations=violations,
            score=score,
            revision_needed=revision,
            abort_needed=abort,
        )

        if not verdict.passed:
            logger.warning(
                "Constitutional evaluation: %d violations (score=%.2f, abort=%s)",
                len(violations),
                score,
                abort,
            )

        return verdict

    def _structural_check(
        self,
        principle: Principle,
        output: dict[str, Any],
        context: dict[str, Any],
    ) -> Violation | None:
        """Run structural (non-LLM) checks for a principle."""

        if principle.evaluator == "reality_level_check":
            return self._check_reality_level(principle, output, context)
        if principle.evaluator == "protected_paths_check":
            return self._check_protected_paths(principle, output, context)
        if principle.evaluator == "metacognitive_honesty_check":
            return self._check_metacognitive_honesty(principle, output, context)

        # Other evaluators require meta-level LLM evaluation
        return None

    def _check_reality_level(
        self,
        principle: Principle,
        output: dict[str, Any],
        context: dict[str, Any],
    ) -> Violation | None:
        """Ensure reality level is declared on state mutations."""
        if output.get("mutates_state", False) and "reality_level" not in output:
            return Violation(
                principle=principle,
                context=str(output.get("action", "unknown")),
                explanation="State mutation without reality level declaration.",
            )
        return None

    def _check_protected_paths(
        self,
        principle: Principle,
        output: dict[str, Any],
        context: dict[str, Any],
    ) -> Violation | None:
        """Check if output targets protected filesystem paths."""
        PROTECTED = (
            "/System/Volumes/Data/System/Library/AssetsV2",
            "/System/Volumes/Data/private/var/db",
            "Library/Mobile Documents",
            "Library/Application Support/CloudDocs",
        )
        target = output.get("target_path", "")
        if any(p in target for p in PROTECTED):
            return Violation(
                principle=principle,
                context=target,
                explanation=f"Attempted write to protected path: {target}",
            )
        return None

    def _check_metacognitive_honesty(
        self,
        principle: Principle,
        output: dict[str, Any],
        context: dict[str, Any],
    ) -> Violation | None:
        """Detect confidence level misrepresentation."""
        confidence = output.get("confidence")
        reasoning_steps = output.get("reasoning_steps", [])

        if confidence is not None and confidence > 0.9 and len(reasoning_steps) == 0:
            return Violation(
                principle=principle,
                context="High confidence with zero reasoning steps",
                explanation=(
                    "Claimed C5-level confidence without any reasoning trace. "
                    "This pattern suggests fabricated certainty."
                ),
            )
        return None
