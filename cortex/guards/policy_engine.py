import os
import re
from typing import Any

import yaml
from pydantic import BaseModel, Field

from cortex.guards.verdicts import PolicyVerdict, VerdictReport

try:
    import cortex_core_rs

    HAS_RUST_CORE = True
except ImportError:
    HAS_RUST_CORE = False


class RuleDefinition(BaseModel):
    id: str
    description: str
    action: str
    severity: str
    patterns: list[str] | None = None
    detect: list[str] | None = None
    commands: list[str] | None = None
    without: list[str] | None = None
    requires: str | None = None


class GuardDefinitions(BaseModel):
    critical: list[RuleDefinition] | None = Field(default_factory=list)
    high: list[RuleDefinition] | None = Field(default_factory=list)
    advisory: list[RuleDefinition] | None = Field(default_factory=list)


class PolicySchema(BaseModel):
    version: str
    schema_ref: str = Field(alias="schema")
    gateway: dict[str, Any]
    guards: GuardDefinitions
    ledger: dict[str, Any]
    rollback: dict[str, Any]
    output: dict[str, Any]
    integrations: dict[str, Any]


class AgenticPolicyEngine:
    def __init__(self, policy_path: str = "cortex.policy.yaml"):
        self.policy_path = policy_path
        self.policy: PolicySchema | None = None
        self._compiled_patterns = {}
        self._native_engine = None

        if HAS_RUST_CORE and os.path.exists(self.policy_path):
            try:
                self._native_engine = cortex_core_rs.NativePolicyEngine(self.policy_path)
            except Exception:  # noqa: S110
                pass

        self.load_policy()

    def load_policy(self):
        """Loads and parses the policy yaml into Pydantic models."""
        if not os.path.exists(self.policy_path):
            raise FileNotFoundError(f"Policy file {self.policy_path} not found.")

        with open(self.policy_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.policy = PolicySchema(**data)
        self._compile_rules()

    def _compile_rules(self):
        """Pre-compiles regex patterns for performance."""
        if not self.policy:
            return

        # Flatten all rules
        critical_rules = self.policy.guards.critical or []
        high_rules = self.policy.guards.high or []
        advisory_rules = self.policy.guards.advisory or []
        all_rules = critical_rules + high_rules + advisory_rules

        for rule in all_rules:
            patterns = rule.patterns or rule.detect or rule.commands or []
            self._compiled_patterns[rule.id] = []
            for p in patterns:
                # We compile with IGNORECASE where it might make sense,
                # but standard policy uses exact cases mostly.
                try:
                    self._compiled_patterns[rule.id].append(re.compile(p))
                except re.error:
                    # In a production system, we log the regex failure.
                    pass

    def evaluate_action(self, action_type: str, payload: str) -> VerdictReport:
        """
        Evaluates a payload against all defined policy guards.
        Returns the most severe VerdictReport.
        """
        if self._native_engine:
            verdict_str, rule_id, desc, sev = self._native_engine.evaluate_action(
                action_type, payload
            )
            return VerdictReport(
                verdict=PolicyVerdict(verdict_str), rule_id=rule_id, description=desc, severity=sev
            )

        if not self.policy:
            return VerdictReport(verdict=PolicyVerdict.CORTEX_PASS)

        # Check P0 (critical) - BLOCKS
        for rule in self.policy.guards.critical or []:
            if self._matches_rule(rule, payload):
                return VerdictReport(
                    verdict=PolicyVerdict.CORTEX_BLOCK,
                    rule_id=rule.id,
                    description=rule.description,
                    severity=rule.severity,
                )

        # Check P1 (high) - WARNS
        for rule in self.policy.guards.high or []:
            if self._matches_rule(rule, payload):
                return VerdictReport(
                    verdict=PolicyVerdict.CORTEX_WARN,
                    rule_id=rule.id,
                    description=rule.description,
                    severity=rule.severity,
                )

        # Check P2 (advisory) - LOGS (We will return PASS but could emit a log internally)
        for rule in self.policy.guards.advisory or []:
            if self._matches_rule(rule, payload):
                # Optionally return a WARN or a new LOG verdict.
                # For now, advisory just returns PASS but might be processed later if needed.
                pass

        return VerdictReport(verdict=PolicyVerdict.CORTEX_PASS)

    def _matches_rule(self, rule: RuleDefinition, payload: str) -> bool:
        # Check exclusion `without` logic if defined
        if rule.without:
            for w in rule.without:
                if w in payload:
                    return False

        # Match compiled patterns
        compiled = self._compiled_patterns.get(rule.id, [])
        for c in compiled:
            if c.search(payload):
                return True
        return False
