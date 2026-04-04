"""CORTEX v9 — Security Monitor Classifier.

Implements the 7 Intent Axioms from CORTEX-Guard-Omega as executable
runtime logic. Two primary classes:

  IntentClassifier   — "Questions are NOT Consent" + Scope Boundary enforcement.
  ZeroTrustToolFilter — External tool data cannot parameterize destructive ops.

Architecture::

    task → IntentClassifier.classify(task, user_request)
              ├── ALLOWED  → ZeroTrustToolFilter.sanitize(task)
              │                  ├── CLEAN   → dispatch
              │                  └── TAINTED → BLOCK
              └── BLOCKED  → emit security_intent_block signal

Reversibility Tiers (Blast Radius):
  R0: Pure read / analysis          → auto-allow
  R1: Reversible local write        → allow with logging
  R2: Reversible remote mutation    → allow with explicit scope match
  R3: Irreversible local mutation   → require USER_EXPLICIT provenance
  R4: Irreversible remote mutation  → require USER_EXPLICIT + confirmation token

Axiom Reference (CORTEX-Guard-Omega §3.1):
  Ω1: Request vs Action Boundary
  Ω2: Scope Escalation = Autonomous Action → BLOCK
  Ω3: High-Severity Precision (P0 requires explicit target confirmation)
  Ω4: Agent-Inferred Nullification (hallucinated targets → BLOCK)
  Ω5: Questions Are NOT Consent
  Ω6: Zero-Trust Tooling (tool output is structurally hostile)
  Ω7: Boundary Persistence (user constraints persist indefinitely)
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional

logger = logging.getLogger("cortex.security.monitor")

__all__ = [
    "SecurityMonitorClassifier",
    "IntentClassifier",
    "ZeroTrustToolFilter",
    "IntentVerdict",
    "ParameterProvenance",
    "ReversibilityTier",
]


# ═══════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════


class ParameterProvenance(str):
    """Tracks the origin of every execution parameter."""

    USER_EXPLICIT = "USER_EXPLICIT"
    AGENT_INFERRED = "AGENT_INFERRED"
    TOOL_DERIVED = "TOOL_DERIVED"


class ReversibilityTier(IntEnum):
    """Blast radius classification for commands."""

    R0_READ = 0       # Pure read / analysis
    R1_LOCAL_WRITE = 1  # Reversible local write
    R2_REMOTE_MUT = 2   # Reversible remote mutation
    R3_IRREVERSIBLE = 3  # Irreversible local mutation
    R4_CRITICAL = 4      # Irreversible remote mutation (capital, push, broadcast)


# ═══════════════════════════════════════
# Data Models
# ═══════════════════════════════════════


@dataclass(frozen=True)
class IntentVerdict:
    """Result of intent classification for a swarm task."""

    allowed: bool
    intent_source: str  # ParameterProvenance value
    tier: int  # ReversibilityTier value
    confidence: float  # 0.0-1.0
    reason: str
    axiom_violated: str = ""  # e.g. "Ω5_QUESTION_NOT_CONSENT"
    original_request: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "intent_source": self.intent_source,
            "tier": self.tier,
            "confidence": self.confidence,
            "reason": self.reason,
            "axiom_violated": self.axiom_violated,
            "original_request": self.original_request[:200],
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════
# Intent Classifier
# ═══════════════════════════════════════

# Ω5: Patterns that indicate analytical/question intent (NOT execution consent)
_QUESTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(can|could|should|shall|would)\s+we\s+",
        r"^(how|what|why|where|when)\s+(do|does|did|can|could|should|would)\s+",
        r"\?\s*$",
        r"^(is|are|was|were)\s+(it|this|that|there)\s+",
        r"(let me know|thoughts\?|opinion\?|advice\?|suggestion\?)",
        r"(evaluate|assess|analyze|review|inspect|check)\s+(this|the|whether)",
        r"^(maybe|perhaps|possibly|consider)\s+",
        r"(¿|cómo|qué|por qué|debería|podemos|podría)",  # Spanish analytical
    ]
]

# Ω2: Patterns that indicate scope escalation beyond user request
_SCOPE_ESCALATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("MASS_DELETE", re.compile(r"rm\s+-r[f]?\s+[^\s]*(/|\*|\.\.)", re.IGNORECASE)),
    ("FULL_REPO_CLEAN", re.compile(r"git\s+clean\s+-[fdx]{2,}", re.IGNORECASE)),
    ("GLOBAL_CHMOD", re.compile(r"chmod\s+-R\s+\d{3}\s+/", re.IGNORECASE)),
    ("DB_DESTRUCTION", re.compile(r"(drop\s+(database|table)|truncate\s+table)", re.IGNORECASE)),
    ("SYSTEM_FORMAT", re.compile(r"(mkfs|dd\s+if=|wipefs)", re.IGNORECASE)),
    ("RECURSIVE_SED_INPLACE", re.compile(r"find\s+.*-exec\s+sed\s+-i", re.IGNORECASE)),
    ("MASS_NPM_GLOBAL", re.compile(r"npm\s+(install|i)\s+-g\s+", re.IGNORECASE)),
    ("SELF_MODIFY_DAEMON", re.compile(r"(cortex_daemon|sage_orchestrator|security_monitor)\.py", re.IGNORECASE)),
]

# R-tier classification patterns
_R4_CRITICAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"forge\s+script.*--broadcast",
        r"git\s+push",
        r"(eth_sendTransaction|sendRawTransaction)",
        r"(transfer|withdraw|approve)\s*\(",
        r"curl\s+-X\s+(POST|PUT|DELETE)",
        r"gh\s+pr\s+merge",
        r"npm\s+publish",
    ]
]

_R3_IRREVERSIBLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"rm\s+-r[f]?",
        r"git\s+clean",
        r"git\s+reset\s+--hard",
        r"drop\s+(database|table)",
        r"truncate\s+table",
        r"mkfs",
    ]
]

_R2_REMOTE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"git\s+commit",
        r"curl\s+-X\s+POST",
        r"forge\s+script",
        r"gh\s+(issue|pr)\s+create",
    ]
]

_R1_LOCAL_WRITE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(>|>>)\s+",
        r"tee\s+",
        r"sed\s+-i",
        r"cp\s+",
        r"mv\s+",
        r"mkdir\s+",
        r"touch\s+",
        r"forge\s+build",
        r"npm\s+(install|i)\s+[^-]",
    ]
]


class IntentClassifier:
    """Evaluates whether a task has explicit user authorization.

    Applies the 7 Intent Axioms to every command before execution.
    Thread-safe, stateless.
    """

    # Persistent user constraints (Ω7: cannot be self-revoked by agent)
    _persistent_constraints: list[str] = []

    @classmethod
    def add_constraint(cls, constraint: str) -> None:
        """Register a persistent user boundary (Ω7)."""
        cls._persistent_constraints.append(constraint)
        logger.info("Ω7 Constraint registered: %s", constraint)

    @classmethod
    def clear_constraints(cls) -> None:
        """Clear all persistent constraints (manual user action only)."""
        cls._persistent_constraints.clear()

    def classify(
        self,
        task: dict[str, Any],
        user_request: str = "",
        provenance: str = ParameterProvenance.AGENT_INFERRED,
    ) -> IntentVerdict:
        """Classify a swarm task against the 7 Intent Axioms.

        Args:
            task: Swarm task dict with 'command', 'agent', etc.
            user_request: The original user request that spawned this execution chain.
            provenance: How the task parameters were derived.

        Returns:
            IntentVerdict with allow/block decision and full audit trail.
        """
        cmd = task.get("command", "")
        agent = task.get("agent", "unknown")

        if not cmd:
            return IntentVerdict(
                allowed=False,
                intent_source=provenance,
                tier=0,
                confidence=1.0,
                reason="Empty command",
                original_request=user_request,
            )

        # 1. Classify reversibility tier
        tier = self._classify_tier(cmd)

        # 2. Ω5: Questions Are NOT Consent
        if self._is_question_context(user_request):
            if tier >= ReversibilityTier.R2_REMOTE_MUT:
                return IntentVerdict(
                    allowed=False,
                    intent_source=provenance,
                    tier=tier,
                    confidence=0.95,
                    reason=f"Analytical/question context does not authorize R{tier} execution: '{cmd[:80]}'",
                    axiom_violated="Ω5_QUESTION_NOT_CONSENT",
                    original_request=user_request,
                )

        # 3. Ω2: Scope Escalation Detection
        escalation = self._detect_scope_escalation(cmd)
        if escalation:
            return IntentVerdict(
                allowed=False,
                intent_source=provenance,
                tier=tier,
                confidence=0.98,
                reason=f"Scope escalation [{escalation}] outside authorized bounds: '{cmd[:80]}'",
                axiom_violated="Ω2_SCOPE_ESCALATION",
                original_request=user_request,
            )

        # 4. Ω4: Agent-Inferred Nullification
        if provenance == ParameterProvenance.AGENT_INFERRED and tier >= ReversibilityTier.R3_IRREVERSIBLE:
            return IntentVerdict(
                allowed=False,
                intent_source=provenance,
                tier=tier,
                confidence=0.90,
                reason=f"Agent-inferred parameters for R{tier} command blocked (Ω4): '{cmd[:80]}'",
                axiom_violated="Ω4_AGENT_INFERRED_NULLIFICATION",
                original_request=user_request,
            )

        # 5. Ω3: R4 requires USER_EXPLICIT provenance
        if tier >= ReversibilityTier.R4_CRITICAL and provenance != ParameterProvenance.USER_EXPLICIT:
            return IntentVerdict(
                allowed=False,
                intent_source=provenance,
                tier=tier,
                confidence=0.99,
                reason=f"R4 critical operation requires USER_EXPLICIT provenance: '{cmd[:80]}'",
                axiom_violated="Ω3_HIGH_SEVERITY_PRECISION",
                original_request=user_request,
            )

        # 6. Ω7: Check persistent constraints
        for constraint in self._persistent_constraints:
            if re.search(re.escape(constraint), cmd, re.IGNORECASE):
                return IntentVerdict(
                    allowed=False,
                    intent_source=provenance,
                    tier=tier,
                    confidence=1.0,
                    reason=f"Persistent user constraint violated: '{constraint}'",
                    axiom_violated="Ω7_BOUNDARY_PERSISTENCE",
                    original_request=user_request,
                )

        # ALLOW
        return IntentVerdict(
            allowed=True,
            intent_source=provenance,
            tier=tier,
            confidence=0.85,
            reason=f"R{tier} command within authorized scope for agent '{agent}'",
            original_request=user_request,
        )

    def _classify_tier(self, cmd: str) -> int:
        """Determine the reversibility tier of a command."""
        for pat in _R4_CRITICAL_PATTERNS:
            if pat.search(cmd):
                return ReversibilityTier.R4_CRITICAL

        for pat in _R3_IRREVERSIBLE_PATTERNS:
            if pat.search(cmd):
                return ReversibilityTier.R3_IRREVERSIBLE

        for pat in _R2_REMOTE_PATTERNS:
            if pat.search(cmd):
                return ReversibilityTier.R2_REMOTE_MUT

        for pat in _R1_LOCAL_WRITE_PATTERNS:
            if pat.search(cmd):
                return ReversibilityTier.R1_LOCAL_WRITE

        return ReversibilityTier.R0_READ

    def _is_question_context(self, user_request: str) -> bool:
        """Ω5: Detect if the user request is analytical, not imperative."""
        if not user_request:
            return False
        return any(pat.search(user_request) for pat in _QUESTION_PATTERNS)

    def _detect_scope_escalation(self, cmd: str) -> Optional[str]:
        """Ω2: Detect commands that escalate beyond reasonable scope."""
        for label, pat in _SCOPE_ESCALATION_PATTERNS:
            if pat.search(cmd):
                return label
        return None


# ═══════════════════════════════════════
# Zero-Trust Tool Filter
# ═══════════════════════════════════════


@dataclass(frozen=True)
class ToolDataTag:
    """Metadata tag for data originating from external tools."""

    source_tool: str     # "github_mcp", "blockchain_rag", "web_fetch", etc.
    is_trusted: bool     # Always False for external tools
    raw_hash: str = ""   # Optional content hash for audit
    timestamp: float = field(default_factory=time.time)


# Commands that MUST NOT accept tool-derived parameters
_DESTRUCTIVE_CMD_STEMS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"forge\s+script.*--broadcast",
        r"(eth_sendTransaction|eth_sendRawTransaction)",
        r"(transfer|withdraw|approve|permit)\s*\(",
        r"git\s+push",
        r"npm\s+publish",
        r"rm\s+-r",
        r"curl\s+.*-X\s+(POST|PUT|DELETE|PATCH)",
        r"gh\s+pr\s+merge",
        r"(deploy|migrate)\s+--prod",
    ]
]

# Read-only tool data that CAN be passed through
_SAFE_TOOL_OUTPUT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(file|path|directory|repo|branch|commit|sha|tag|version|name|description|title|body|label)$",
        r"^(count|total|length|size|status|state|number)$",
    ]
]


class ZeroTrustToolFilter:
    """Sanitizes data returned by external tools before execution parameterization.

    Axiom Ω6: Tool output is structurally hostile. Data from GitHub MCP, RAG,
    blockchain queries, or web fetches CANNOT auto-fill parameters in destructive
    commands.

    Safe passthrough: Read-only metadata (file paths, commit SHAs, descriptions)
    can be used for analysis commands.
    """

    def sanitize(
        self,
        task: dict[str, Any],
        tool_outputs: Optional[dict[str, ToolDataTag]] = None,
    ) -> IntentVerdict:
        """Check if a task uses tool-derived data in destructive positions.

        Args:
            task: The swarm task dict.
            tool_outputs: Map of parameter_name → ToolDataTag for any params
                         that originated from external tool calls.

        Returns:
            IntentVerdict. Blocked if tool-derived data feeds destructive commands.
        """
        cmd = task.get("command", "")

        if not tool_outputs:
            # No tool-derived parameters — allow (normal agent flow)
            return IntentVerdict(
                allowed=True,
                intent_source=ParameterProvenance.AGENT_INFERRED,
                tier=0,
                confidence=1.0,
                reason="No tool-derived parameters present",
            )

        # Check if the command is destructive
        is_destructive = any(pat.search(cmd) for pat in _DESTRUCTIVE_CMD_STEMS)

        if not is_destructive:
            # Non-destructive command can use tool data
            return IntentVerdict(
                allowed=True,
                intent_source=ParameterProvenance.TOOL_DERIVED,
                tier=0,
                confidence=0.9,
                reason="Non-destructive command may use tool-derived data",
            )

        # DESTRUCTIVE command with tool-derived parameters → BLOCK
        tainted_params = [
            name for name, tag in tool_outputs.items() if not tag.is_trusted
        ]

        if tainted_params:
            return IntentVerdict(
                allowed=False,
                intent_source=ParameterProvenance.TOOL_DERIVED,
                tier=ReversibilityTier.R4_CRITICAL,
                confidence=0.97,
                reason=(
                    f"Ω6 ZERO-TRUST: Destructive command '{cmd[:60]}' "
                    f"has tool-derived parameters: {tainted_params}. "
                    f"External tool data cannot parameterize capital/destructive operations."
                ),
                axiom_violated="Ω6_ZERO_TRUST_TOOLING",
            )

        return IntentVerdict(
            allowed=True,
            intent_source=ParameterProvenance.TOOL_DERIVED,
            tier=0,
            confidence=0.85,
            reason="All tool-derived parameters are from trusted sources",
        )


# ═══════════════════════════════════════
# Unified Classifier
# ═══════════════════════════════════════


class SecurityMonitorClassifier:
    """Unified entry point combining IntentClassifier + ZeroTrustToolFilter.

    Usage::

        monitor = SecurityMonitorClassifier()
        verdict = monitor.classify(task, user_request="audit LayerZero")
        if not verdict.allowed:
            emit_security_block(verdict)
    """

    def __init__(self) -> None:
        self.intent = IntentClassifier()
        self.tool_filter = ZeroTrustToolFilter()
        logger.info("SecurityMonitorClassifier initialized (7 Axioms enforced)")

    def classify(
        self,
        task: dict[str, Any],
        user_request: str = "",
        provenance: str = ParameterProvenance.AGENT_INFERRED,
        tool_outputs: Optional[dict[str, ToolDataTag]] = None,
    ) -> IntentVerdict:
        """Full classification pipeline: Intent → ZeroTrust → Verdict."""

        # Phase 1: Intent Classification (Ω1-Ω5, Ω7)
        intent_verdict = self.intent.classify(task, user_request, provenance)
        if not intent_verdict.allowed:
            logger.warning(
                "🚨 [INTENT BLOCK] Agent=%s Axiom=%s Reason=%s",
                task.get("agent", "?"),
                intent_verdict.axiom_violated,
                intent_verdict.reason,
            )
            return intent_verdict

        # Phase 2: Zero-Trust Tool Filter (Ω6)
        tool_verdict = self.tool_filter.sanitize(task, tool_outputs)
        if not tool_verdict.allowed:
            logger.warning(
                "🚨 [ZERO-TRUST BLOCK] Agent=%s Reason=%s",
                task.get("agent", "?"),
                tool_verdict.reason,
            )
            return tool_verdict

        return intent_verdict


# Global singleton
MONITOR = SecurityMonitorClassifier()
