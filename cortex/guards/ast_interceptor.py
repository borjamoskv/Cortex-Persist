"""
cortex/guards/ast_interceptor.py
────────────────────────────────
AST Gateway — Zero-Trust Sidecar Interceptor (Ω1, Ω2, Ω3)

Intercepts agent I/O payloads BEFORE tool execution.
Validates structural integrity via AST parsing and JSON Schema enforcement.
Byzantine actors produce stochastic output → this guard forces deterministic
boundaries or rejects with constraint-based feedback for self-correction.

Architecture:
  [ Agent Swarm ] --(Payload)--> [ AST Gateway ] --[OK]--> [ Tool Call ]
                                       |
                                  [FAIL: Quarantine] --> [ State Quarantine ]
                                       |                       |
                                  [ Taint Log ]           [ Telemetry ]
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger("cortex.guards.ast_interceptor")


# ── Verdict ──────────────────────────────────────────────────────────────────

class Verdict(Enum):
    PASS = auto()
    QUARANTINE = auto()
    REJECT = auto()


@dataclass(frozen=True)
class InterceptionResult:
    """Deterministic result of payload interception."""
    verdict: Verdict
    payload_hash: str
    agent_id: str
    tool_name: str
    timestamp: float
    violations: list[str] = field(default_factory=list)
    constraint_feedback: dict[str, Any] | None = None
    quarantine_id: str | None = None

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.PASS

    def to_ledger_entry(self) -> dict[str, Any]:
        """Emission format for Master Ledger append."""
        return {
            "type": "ast_interception",
            "verdict": self.verdict.name,
            "payload_hash": self.payload_hash,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "violations": self.violations,
            "quarantine_id": self.quarantine_id,
        }


# ── Schema Enforcer ─────────────────────────────────────────────────────────

@dataclass
class SchemaConstraint:
    """Strict schema for a tool call parameter."""
    name: str
    type: str  # "str", "int", "float", "bool", "list", "dict", "null"
    required: bool = True
    max_length: int | None = None
    pattern: str | None = None  # regex for str fields
    allowed_values: list[Any] | None = None
    nested_schema: list[SchemaConstraint] | None = None


class StrictSchemaEnforcer:
    """
    Validates tool call payloads against registered schemas.
    No schema registered → REJECT (fail-closed).
    """

    def __init__(self) -> None:
        self._schemas: dict[str, list[SchemaConstraint]] = {}

    def register(self, tool_name: str, constraints: list[SchemaConstraint]) -> None:
        self._schemas[tool_name] = constraints

    def validate(self, tool_name: str, payload: dict[str, Any]) -> list[str]:
        """Returns list of violations. Empty = valid."""
        if tool_name not in self._schemas:
            return [f"No schema registered for tool '{tool_name}' — FAIL-CLOSED"]

        violations = []
        schema = self._schemas[tool_name]

        for constraint in schema:
            value = payload.get(constraint.name)

            if value is None and constraint.required:
                violations.append(f"Missing required field: '{constraint.name}'")
                continue

            if value is None:
                continue

            # Type check
            expected_type = {
                "str": str, "int": int, "float": (int, float),
                "bool": bool, "list": list, "dict": dict,
            }.get(constraint.type)

            if expected_type and not isinstance(value, expected_type):
                violations.append(
                    f"Type violation: '{constraint.name}' expected "
                    f"{constraint.type}, got {type(value).__name__}"
                )

            # Length check
            if constraint.max_length and isinstance(value, str) and len(value) > constraint.max_length:
                violations.append(
                    f"Length violation: '{constraint.name}' exceeds "
                    f"max {constraint.max_length} chars (got {len(value)})"
                )

            # Allowed values
            if constraint.allowed_values and value not in constraint.allowed_values:
                violations.append(
                    f"Value violation: '{constraint.name}' = {value!r} "
                    f"not in {constraint.allowed_values}"
                )

        # Check for undeclared fields (strict mode)
        declared = {c.name for c in schema}
        undeclared = set(payload.keys()) - declared
        if undeclared:
            violations.append(f"Undeclared fields: {undeclared} — possible injection vector")

        return violations


# ── AST Safety Analyzer ─────────────────────────────────────────────────────

class ASTSafetyAnalyzer:
    """
    Parses Python code payloads via AST to detect dangerous constructs.
    This is NOT execution — it's structural analysis only.
    """

    DANGEROUS_CALLS = frozenset({
        "eval", "exec", "compile", "__import__",
        "os.system", "subprocess.run", "subprocess.call",
        "subprocess.Popen", "os.popen", "os.execv",
    })

    DANGEROUS_ATTRS = frozenset({
        "__class__", "__subclasses__", "__globals__",
        "__builtins__", "__code__", "__reduce__",
    })

    @classmethod
    def analyze(cls, code: str) -> list[str]:
        """Parse code string and return list of safety violations."""
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            violations.append(f"Syntax error in payload: {e}")
            return violations

        for node in ast.walk(tree):
            # Dangerous function calls
            if isinstance(node, ast.Call):
                call_name = cls._resolve_call_name(node)
                if call_name and call_name in cls.DANGEROUS_CALLS:
                    violations.append(
                        f"Dangerous call detected: {call_name}() at line {node.lineno}"
                    )

            # Dangerous attribute access
            if isinstance(node, ast.Attribute):
                if node.attr in cls.DANGEROUS_ATTRS:
                    violations.append(
                        f"Dangerous attr access: .{node.attr} at line {node.lineno}"
                    )

            # Import of dangerous modules
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("os", "subprocess", "shutil", "ctypes"):
                        violations.append(
                            f"Restricted import: {alias.name} at line {node.lineno}"
                        )

        return violations

    @staticmethod
    def _resolve_call_name(node: ast.Call) -> str | None:
        """Resolve the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
        return None


# ── State Quarantine ─────────────────────────────────────────────────────────

@dataclass
class QuarantinedPayload:
    """A payload that failed validation, held for SRE telemetry."""
    quarantine_id: str
    agent_id: str
    tool_name: str
    payload_hash: str
    violations: list[str]
    raw_payload: dict[str, Any]
    timestamp: float
    resolved: bool = False


class StateQuarantine:
    """
    Holds contaminated payloads in strict isolation.
    Generates immutable telemetry for SRE without affecting uptime.
    """

    def __init__(self, max_capacity: int = 10_000) -> None:
        self._entries: dict[str, QuarantinedPayload] = {}
        self._max_capacity = max_capacity

    def quarantine(
        self,
        agent_id: str,
        tool_name: str,
        payload: dict[str, Any],
        violations: list[str],
    ) -> QuarantinedPayload:
        """Admit a contaminated payload into quarantine."""
        ts = time.time()
        payload_hash = self._hash_payload(payload)
        qid = f"Q-{hashlib.sha256(f'{agent_id}:{ts}'.encode()).hexdigest()[:12]}"

        entry = QuarantinedPayload(
            quarantine_id=qid,
            agent_id=agent_id,
            tool_name=tool_name,
            payload_hash=payload_hash,
            violations=violations,
            raw_payload=payload,
            timestamp=ts,
        )

        # Evict oldest if at capacity
        if len(self._entries) >= self._max_capacity:
            oldest_key = min(self._entries, key=lambda k: self._entries[k].timestamp)
            del self._entries[oldest_key]

        self._entries[qid] = entry
        logger.warning("[QUARANTINE] %s — agent=%s tool=%s violations=%d", qid, agent_id, tool_name, len(violations))
        return entry

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def unresolved(self) -> list[QuarantinedPayload]:
        return [e for e in self._entries.values() if not e.resolved]

    def get(self, quarantine_id: str) -> QuarantinedPayload | None:
        return self._entries.get(quarantine_id)

    def telemetry_snapshot(self) -> dict[str, Any]:
        """Cold telemetry emission for SRE dashboards."""
        return {
            "total_quarantined": self.count,
            "unresolved": len(self.unresolved),
            "by_agent": self._group_by("agent_id"),
            "by_tool": self._group_by("tool_name"),
            "violation_frequency": self._violation_freq(),
        }

    def _group_by(self, field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self._entries.values():
            key = getattr(e, field)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _violation_freq(self) -> dict[str, int]:
        freq: dict[str, int] = {}
        for e in self._entries.values():
            for v in e.violations:
                category = v.split(":")[0].strip()
                freq[category] = freq.get(category, 0) + 1
        return freq

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Main Interceptor ─────────────────────────────────────────────────────────

class ASTInterceptor:
    """
    Drop-In Sidecar Proxy for Agent-to-Tool calls.

    Does NOT audit agent "thinking". Only intercepts the I/O payload
    at the tool boundary in microseconds.

    Pipeline:
      payload → schema validation → AST safety analysis → taint signature
      → [PASS: emit to tool] | [FAIL: quarantine + constraint feedback]
    """

    def __init__(self) -> None:
        self.schema_enforcer = StrictSchemaEnforcer()
        self.quarantine = StateQuarantine()
        self._interception_count = 0
        self._pass_count = 0
        self._reject_count = 0

    def register_tool_schema(
        self,
        tool_name: str,
        constraints: list[SchemaConstraint],
    ) -> None:
        """Register a strict schema for a tool. Unregistered tools get REJECTED."""
        self.schema_enforcer.register(tool_name, constraints)

    def intercept(
        self,
        agent_id: str,
        tool_name: str,
        payload: dict[str, Any],
    ) -> InterceptionResult:
        """
        Intercept a tool call payload. Returns a deterministic verdict.

        If the payload contains a 'code' field with Python source,
        it also undergoes AST safety analysis.
        """
        ts = time.time()
        self._interception_count += 1
        payload_hash = StateQuarantine._hash_payload(payload)

        violations: list[str] = []

        # 1. Schema validation
        schema_violations = self.schema_enforcer.validate(tool_name, payload)
        violations.extend(schema_violations)

        # 2. AST safety analysis (if payload contains code)
        code_field = payload.get("code") or payload.get("source") or payload.get("script")
        if code_field and isinstance(code_field, str):
            ast_violations = ASTSafetyAnalyzer.analyze(code_field)
            violations.extend(ast_violations)

        # 3. Determine verdict
        if not violations:
            self._pass_count += 1
            verdict = Verdict.PASS
            quarantine_id = None
            constraint_feedback = None
        else:
            self._reject_count += 1
            verdict = Verdict.QUARANTINE

            # Quarantine the payload
            entry = self.quarantine.quarantine(agent_id, tool_name, payload, violations)
            quarantine_id = entry.quarantine_id

            # Generate constraint feedback for agent self-correction (Cycle N+1)
            constraint_feedback = self._build_constraint_feedback(tool_name, violations)

        result = InterceptionResult(
            verdict=verdict,
            payload_hash=payload_hash,
            agent_id=agent_id,
            tool_name=tool_name,
            timestamp=ts,
            violations=violations,
            constraint_feedback=constraint_feedback,
            quarantine_id=quarantine_id,
        )

        logger.info(
            "[INTERCEPT] %s | agent=%s tool=%s hash=%s violations=%d",
            verdict.name, agent_id, tool_name, payload_hash, len(violations),
        )

        return result

    def _build_constraint_feedback(
        self,
        tool_name: str,
        violations: list[str],
    ) -> dict[str, Any]:
        """
        Strict JSON constraint returned to the agent swarm.
        Forces self-correction without human intervention.
        """
        return {
            "error": "CORTEX_AST_INTERCEPTION",
            "tool": tool_name,
            "violation_count": len(violations),
            "violations": violations,
            "instruction": (
                "Your payload was rejected by the CORTEX AST Gateway. "
                "Fix the listed violations and retry. "
                "DO NOT attempt to bypass schema constraints."
            ),
            "retry_allowed": True,
            "max_retries": 3,
        }

    # ── Telemetry ────────────────────────────────────────────────────────

    def telemetry(self) -> dict[str, Any]:
        """Cold telemetry for Master Ledger and SRE dashboards."""
        return {
            "total_interceptions": self._interception_count,
            "passed": self._pass_count,
            "rejected": self._reject_count,
            "rejection_rate": (
                self._reject_count / self._interception_count
                if self._interception_count > 0 else 0.0
            ),
            "quarantine": self.quarantine.telemetry_snapshot(),
        }


# ── Shadow Run (Proof of Poison) ────────────────────────────────────────────

class ShadowRun:
    """
    Watch-Only mode: intercepts but NEVER blocks.
    Records what WOULD have been quarantined.
    After 72h, emits a Proof of Poison report.

    This is the zero-friction sales mechanism:
    Deploy → Watch → Emit evidence → Client self-activates.
    """

    def __init__(self, interceptor: ASTInterceptor) -> None:
        self._interceptor = interceptor
        self._shadow_log: list[InterceptionResult] = []
        self._start_time = time.time()

    def shadow_intercept(
        self,
        agent_id: str,
        tool_name: str,
        payload: dict[str, Any],
    ) -> InterceptionResult:
        """Run interception but ALWAYS pass through. Log what would have failed."""
        result = self._interceptor.intercept(agent_id, tool_name, payload)

        if not result.passed:
            self._shadow_log.append(result)

        # Always pass through in shadow mode
        return InterceptionResult(
            verdict=Verdict.PASS,
            payload_hash=result.payload_hash,
            agent_id=result.agent_id,
            tool_name=result.tool_name,
            timestamp=result.timestamp,
            violations=[],
            constraint_feedback=None,
            quarantine_id=None,
        )

    def proof_of_poison(self) -> dict[str, Any]:
        """
        Cryptographic proof of every silent failure detected.
        The sale doesn't negotiate — it activates by fiduciary panic.
        """
        elapsed_h = (time.time() - self._start_time) / 3600

        poison_entries = []
        for result in self._shadow_log:
            poison_entries.append({
                "timestamp": result.timestamp,
                "agent_id": result.agent_id,
                "tool_name": result.tool_name,
                "payload_hash": result.payload_hash,
                "violations": result.violations,
                "would_have_corrupted": True,
            })

        # Compute hash chain over all entries for tamper evidence
        chain_hash = hashlib.sha256(b"CORTEX-PROOF-OF-POISON-v1").hexdigest()
        for entry in poison_entries:
            raw = json.dumps(entry, sort_keys=True, default=str)
            chain_hash = hashlib.sha256(f"{chain_hash}:{raw}".encode()).hexdigest()

        return {
            "proof_of_poison": {
                "version": "1.0",
                "observation_window_hours": round(elapsed_h, 2),
                "total_silent_failures_detected": len(poison_entries),
                "chain_hash": chain_hash,
                "entries": poison_entries,
                "summary": (
                    f"During {elapsed_h:.1f}h of shadow observation, "
                    f"CORTEX detected {len(poison_entries)} tool call(s) "
                    f"that would have silently corrupted state without "
                    f"the AST Gateway active."
                ),
            }
        }
