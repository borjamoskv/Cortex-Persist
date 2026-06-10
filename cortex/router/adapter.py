# [C5-REAL] Exergy-Maximized
"""ExergyConfigAdapter — Unidirectional YAML → Contract Bridge.

Architecture Invariants:
    1. Reads YAML policy (cognitive_routing_matrix.yaml). NEVER writes.
    2. Produces RoutingDecision conforming to contract.py schema.
    3. Resolution logic MUST be equivalent to contract.resolve().
    4. If YAML and contract disagree, contract wins (adapter raises).
    5. No runtime state. No caching across calls. No side effects.

Data Flow:
    YAML (policy) → ExergyConfigAdapter.resolve() → RoutingDecision
                                                      ↑
                                            contract.resolve() validates
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from cortex.router.contract import (
    CONTRACT_VERSION,
    CognitiveMode,
    RoutingContext,
    RoutingDecision,
    Severity,
)
from cortex.router.contract import (
    resolve as contract_resolve,
)

logger = logging.getLogger("cortex.router.adapter")

# ─── Constants ────────────────────────────────────────────────────────────

_DEFAULT_YAML_PATH = (
    Path.home() / ".gemini/config/skills/Exergy-Engine-OMEGA/cognitive_routing_matrix.yaml"
)

_SUPPORTED_SCHEMA_VERSIONS = frozenset({"2026.2"})

# ─── Mode Mapping ─────────────────────────────────────────────────────────

_YAML_MODE_MAP: dict[str, CognitiveMode] = {
    "normal": CognitiveMode.NORMAL,
    "deep_think": CognitiveMode.DEEP_THINK,
    "deep_research": CognitiveMode.DEEP_RESEARCH,
    "ultra_think": CognitiveMode.ULTRA_THINK,
}


# ─── Exceptions ───────────────────────────────────────────────────────────


class AdapterSchemaError(Exception):
    """YAML schema version mismatch or structural violation."""


class AdapterContractDrift(Exception):
    """Adapter resolution diverged from contract.resolve() reference.

    This is a FATAL architectural violation. If this fires,
    either the YAML policy or the adapter logic has drifted
    from the canonical contract.
    """


# ─── Loaded Policy ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LoadedPolicy:
    """Immutable snapshot of a loaded YAML policy.

    Created once per load. Never mutated.
    """

    schema_version: str
    subsystem: str
    operator: str
    routing_rules: tuple[dict[str, Any], ...]
    raw: dict[str, Any]


# ─── Adapter ──────────────────────────────────────────────────────────────


class ExergyConfigAdapter:
    """Unidirectional adapter: YAML policy → RoutingDecision.

    Usage:
        adapter = ExergyConfigAdapter()          # loads default YAML
        adapter = ExergyConfigAdapter(path=...)   # loads custom YAML
        decision = adapter.resolve(ctx)           # returns RoutingDecision

    Guarantees:
        - Every resolve() call cross-validates against contract.resolve().
        - AdapterContractDrift is raised on ANY divergence.
        - No internal state mutated between calls.
    """

    def __init__(self, path: Path | None = None, *, strict: bool = True) -> None:
        """Load and validate YAML policy.

        Args:
            path: Path to cognitive_routing_matrix.yaml. Uses default if None.
            strict: If True (default), cross-validate every resolve() against
                    contract.resolve(). Disable only for benchmarking.
        """
        self._path = path or _DEFAULT_YAML_PATH
        self._strict = strict
        self._policy = self._load(self._path)

        logger.info(
            "[ADAPTER] Loaded policy v%s from %s (%d rules)",
            self._policy.schema_version,
            self._path,
            len(self._policy.routing_rules),
        )

    @property
    def policy(self) -> LoadedPolicy:
        """Read-only access to the loaded policy snapshot."""
        return self._policy

    @property
    def contract_version(self) -> str:
        """Contract version this adapter targets."""
        return CONTRACT_VERSION

    # ─── YAML Loading ─────────────────────────────────────────────────

    @staticmethod
    def _load(path: Path) -> LoadedPolicy:
        """Load and validate YAML policy file.

        Raises:
            FileNotFoundError: YAML file does not exist.
            AdapterSchemaError: Schema version unsupported or structure invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"Policy YAML not found: {path}")

        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise AdapterSchemaError(f"YAML root must be a dict, got {type(raw).__name__}")

        version = raw.get("schema_version", "")
        if version not in _SUPPORTED_SCHEMA_VERSIONS:
            raise AdapterSchemaError(
                f"Unsupported schema_version '{version}'. Supported: {_SUPPORTED_SCHEMA_VERSIONS}"
            )

        rules = raw.get("routing_rules")
        if not isinstance(rules, list) or len(rules) == 0:
            raise AdapterSchemaError("routing_rules must be a non-empty list")

        # Validate each rule has required keys
        required_keys = {"id", "condition", "result"}
        for i, rule in enumerate(rules):
            missing = required_keys - set(rule.keys())
            if missing:
                raise AdapterSchemaError(
                    f"Rule {i} ('{rule.get('id', '?')}') missing keys: {missing}"
                )
            if rule["result"] not in _YAML_MODE_MAP:
                raise AdapterSchemaError(
                    f"Rule {i} result '{rule['result']}' not in valid modes: "
                    f"{list(_YAML_MODE_MAP.keys())}"
                )

        return LoadedPolicy(
            schema_version=version,
            subsystem=raw.get("subsystem", "unknown"),
            operator=raw.get("operator", "unknown"),
            routing_rules=tuple(rules),
            raw=raw,
        )

    # ─── Resolution ───────────────────────────────────────────────────

    def resolve(self, ctx: RoutingContext) -> RoutingDecision:
        """Resolve a RoutingContext to a RoutingDecision via YAML policy.

        The adapter evaluates the same short-circuit OR logic defined
        in the YAML routing_rules, mapping each gate to the contract
        schema. If strict mode is enabled, the result is cross-validated
        against contract.resolve().

        Args:
            ctx: Fully populated RoutingContext.

        Returns:
            RoutingDecision conforming to contract.py schema.

        Raises:
            AdapterContractDrift: Adapter result diverges from contract.
        """
        decision = self._evaluate_gates(ctx)

        if self._strict:
            self._cross_validate(ctx, decision)

        return decision

    def _evaluate_gates(self, ctx: RoutingContext) -> RoutingDecision:
        """Evaluate YAML gates in precedence order. First match wins."""
        for rule in self._policy.routing_rules:
            gate_id = rule["id"]
            mode = _YAML_MODE_MAP[rule["result"]]

            if gate_id == "GATE_ULTRA":
                if ctx.severity == Severity.CRITICAL or ctx.blast_radius >= 3:
                    return RoutingDecision(
                        mode=mode,
                        gate_id=gate_id,
                        rationale=(
                            f"severity={ctx.severity.value}, "
                            f"blast_radius={ctx.blast_radius}. "
                            f"YAML rule: {rule.get('rationale', 'N/A')}"
                        ),
                        source="adapter",
                    )

            elif gate_id == "GATE_RESEARCH":
                if ctx.info_state.has_deficit:
                    deficits = []
                    if not ctx.info_state.exists_internally:
                        deficits.append("missing")
                    if not ctx.info_state.is_reliable:
                        deficits.append("unreliable")
                    if not ctx.info_state.is_current:
                        deficits.append("stale")
                    return RoutingDecision(
                        mode=mode,
                        gate_id=gate_id,
                        rationale=f"Information deficit: {', '.join(deficits)}.",
                        source="adapter",
                    )

            elif gate_id == "GATE_DEEP":
                if ctx.blast_radius == 2 or ctx.severity == Severity.HIGH:
                    return RoutingDecision(
                        mode=mode,
                        gate_id=gate_id,
                        rationale=(
                            f"severity={ctx.severity.value}, "
                            f"blast_radius={ctx.blast_radius}. "
                            f"Structural decision requires explicit CoT."
                        ),
                        source="adapter",
                    )

            elif gate_id == "GATE_NORMAL":
                return RoutingDecision(
                    mode=mode,
                    gate_id=gate_id,
                    rationale="Routine operation. No escalation triggers matched.",
                    source="adapter",
                )

        # Unreachable if YAML has GATE_NORMAL as final rule.
        # Defensive fallback — contract always has an answer.
        logger.warning("[ADAPTER] No gate matched — falling back to contract.resolve()")
        return contract_resolve(ctx)

    def _cross_validate(self, ctx: RoutingContext, adapter_decision: RoutingDecision) -> None:
        """Verify adapter decision matches contract.resolve() on mode and gate_id.

        Raises AdapterContractDrift if they diverge.
        """
        contract_decision = contract_resolve(ctx)

        if adapter_decision.mode != contract_decision.mode:
            raise AdapterContractDrift(
                f"MODE DRIFT: adapter={adapter_decision.mode.value} vs "
                f"contract={contract_decision.mode.value} | "
                f"ctx=(severity={ctx.severity.value}, "
                f"blast_radius={ctx.blast_radius}, "
                f"info_deficit={ctx.info_state.has_deficit})"
            )

        if adapter_decision.gate_id != contract_decision.gate_id:
            raise AdapterContractDrift(
                f"GATE DRIFT: adapter={adapter_decision.gate_id} vs "
                f"contract={contract_decision.gate_id} | "
                f"ctx=(severity={ctx.severity.value}, "
                f"blast_radius={ctx.blast_radius}, "
                f"info_deficit={ctx.info_state.has_deficit})"
            )

        logger.debug(
            "[ADAPTER] Cross-validation OK: mode=%s gate=%s",
            adapter_decision.mode.value,
            adapter_decision.gate_id,
        )
