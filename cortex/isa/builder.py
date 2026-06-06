# [C5-REAL] Exergy-Maximized
"""CORTEX Agent ISA Builder - Pythonic DSL for homoiconic dispatch trees.

Every function returns a dict that maps 1:1 to the Rust AgentOp enum
via serde_json. The tree is pure data until it crosses FFI, where it
becomes executable code. This IS code-as-data.

Usage:
    from cortex.isa import dispatch, seq, par, cond, halt, Predicate

    plan = seq(
        bind("target", "bounty_alpha"),
        par(
            dispatch("hunter_a", {"mode": "scan"}, id=1),
            dispatch("hunter_b", {"mode": "extract"}, id=2),
        ),
        cond(
            Predicate.always(),
            then_branch=dispatch("aggregator", {"collect": True}, id=3),
            else_branch=halt(error="no results"),
        ),
    )

    # Serialize (code -> data)
    json_str = to_json(plan)

    # The JSON is directly deserializable by Rust's AgentOp::from_json()

Reality Level: C5-REAL
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

# -----------------------------------------------------------
# S1 - Core Types (mirror Rust enums)
# -----------------------------------------------------------


class MutationOp(str, Enum):
    INSERT = "Insert"
    UPDATE = "Update"
    DELETE = "Delete"
    UPSERT = "Upsert"


class Ref:
    """Reference to a data slot - mirrors Rust Ref enum."""

    @staticmethod
    def named(name: str) -> dict:
        return {"Named": name}

    @staticmethod
    def ledger_key(key: str) -> dict:
        return {"LedgerKey": key}

    @staticmethod
    def index(idx: int) -> dict:
        return {"Index": idx}


class HaltReason:
    """Halt reasons - mirrors Rust HaltReason enum."""

    @staticmethod
    def success() -> str:
        return "Success"

    @staticmethod
    def error(msg: str) -> dict:
        return {"Error": msg}

    @staticmethod
    def circuit_breaker(threshold: float, actual: float) -> dict:
        return {"CircuitBreaker": {"threshold": threshold, "actual": actual}}

    @staticmethod
    def timeout(limit_ms: int) -> dict:
        return {"Timeout": {"limit_ms": limit_ms}}


class SelfQuery:
    """Self-inspection queries - mirrors Rust SelfQuery enum."""

    @staticmethod
    def current_tree() -> str:
        return "CurrentTree"

    @staticmethod
    def node_count() -> str:
        return "NodeCount"

    @staticmethod
    def tree_depth() -> str:
        return "TreeDepth"

    @staticmethod
    def dispatch_targets() -> str:
        return "DispatchTargets"

    @staticmethod
    def exec_stats() -> str:
        return "ExecStats"


class Predicate:
    """Predicates for conditional branching - mirrors Rust Predicate enum."""

    @staticmethod
    def always() -> str:
        return "Always"

    @staticmethod
    def never() -> str:
        return "Never"

    @staticmethod
    def exists(ref: dict) -> dict:
        return {"Exists": ref}

    @staticmethod
    def equals(ref: dict, value: Any) -> dict:
        return {"Equals": [ref, value]}

    @staticmethod
    def greater_than(ref: dict, threshold: float) -> dict:
        return {"GreaterThan": [ref, threshold]}

    @staticmethod
    def less_than(ref: dict, threshold: float) -> dict:
        return {"LessThan": [ref, threshold]}

    @staticmethod
    def and_(a: Any, b: Any) -> dict:
        return {"And": [a, b]}

    @staticmethod
    def or_(a: Any, b: Any) -> dict:
        return {"Or": [a, b]}

    @staticmethod
    def not_(p: Any) -> dict:
        return {"Not": p}


# -----------------------------------------------------------
# S2 - Ledger Types
# -----------------------------------------------------------


@dataclass
class LedgerQuery:
    """Ledger query - mirrors Rust LedgerQuery struct."""

    table: str
    output_ref: dict
    filter: Any | None = None
    limit: int | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"table": self.table, "output_ref": self.output_ref}
        if self.filter is not None:
            d["filter"] = self.filter
        if self.limit is not None:
            d["limit"] = self.limit
        return d


@dataclass
class LedgerMutation:
    """Ledger mutation - mirrors Rust LedgerMutation struct."""

    table: str
    operation: MutationOp
    payload: Any

    def to_dict(self) -> dict:
        return {
            "table": self.table,
            "operation": self.operation.value,
            "payload": self.payload,
        }


# -----------------------------------------------------------
# S3 - AgentOp Type (the dict IS the instruction)
# -----------------------------------------------------------

# AgentOp is just a type alias for dict. The dict maps 1:1 to Rust's
# serde representation. This IS code-as-data: no wrapper classes,
# no indirection - the dict is simultaneously the plan and the data.
AgentOp = dict


# -----------------------------------------------------------
# S4 - Builder DSL Functions
# -----------------------------------------------------------


def dispatch(target: str, payload: Any = None, *, id: int = 0) -> AgentOp:
    """Create a Dispatch operation.

    Args:
        target: Named dispatch target (agent, service, MCP tool)
        payload: JSON-serializable payload
        id: Unique OpId for tree introspection and rewriting
    """
    return {
        "Dispatch": {
            "id": id,
            "target": target,
            "payload": payload if payload is not None else {},
        }
    }


def seq(*ops: AgentOp) -> AgentOp:
    """Sequential execution: ops run in order."""
    return {"Seq": list(ops)}


def par(*ops: AgentOp) -> AgentOp:
    """Parallel execution: ops fan-out via rayon."""
    return {"Par": list(ops)}


def cond(
    predicate: Any,
    then_branch: AgentOp,
    else_branch: AgentOp | None = None,
) -> AgentOp:
    """Conditional branching - evaluated entirely in Rust."""
    return {
        "Cond": {
            "predicate": predicate,
            "then_branch": then_branch,
            "else_branch": else_branch if else_branch is not None else "Noop",
        }
    }


def loop_n(count: int, body: AgentOp) -> AgentOp:
    """Repeat an operation N times."""
    return {
        "Loop": {
            "count": count,
            "body": body,
        }
    }


def bind(name: str, value: Any) -> AgentOp:
    """Bind a value to a named reference in the execution scope."""
    return {
        "Bind": {
            "name": name,
            "value": value,
        }
    }


def transform(input_ref: dict, func: str, output_ref: dict) -> AgentOp:
    """Apply a named function to transform data."""
    return {
        "Transform": {
            "input": input_ref,
            "func": func,
            "output": output_ref,
        }
    }


def query(
    table: str,
    output_ref: dict,
    *,
    filter: Any | None = None,
    limit: int | None = None,
) -> AgentOp:
    """Query the sovereign ledger."""
    q = LedgerQuery(table=table, output_ref=output_ref, filter=filter, limit=limit)
    return {"Query": q.to_dict()}


def mutate(
    table: str,
    operation: MutationOp,
    payload: Any,
) -> AgentOp:
    """Mutate the sovereign ledger."""
    m = LedgerMutation(table=table, operation=operation, payload=payload)
    return {"Mutate": m.to_dict()}


def reflect(sq: Any) -> AgentOp:
    """Introspect the current dispatch tree (code-as-data reflection)."""
    return {"Reflect": sq}


def rewrite(target_id: int, replacement: AgentOp) -> AgentOp:
    """Replace a subtree by OpId (runtime self-modification)."""
    return {
        "Rewrite": {
            "target_id": target_id,
            "replacement": replacement,
        }
    }


def halt(
    *,
    success: bool = False,
    error: str | None = None,
    circuit_breaker: tuple | None = None,
    timeout_ms: int | None = None,
) -> AgentOp:
    """Halt execution with a reason."""
    if error:
        reason = HaltReason.error(error)
    elif circuit_breaker:
        reason = HaltReason.circuit_breaker(*circuit_breaker)
    elif timeout_ms:
        reason = HaltReason.timeout(timeout_ms)
    else:
        reason = HaltReason.success()
    return {"Halt": reason}


def noop() -> AgentOp:
    """No-op placeholder."""
    return "Noop"  # pyright: ignore[reportReturnType]


# -----------------------------------------------------------
# S5 - Serialization Utilities
# -----------------------------------------------------------


def to_json(op: AgentOp, *, indent: int = 2) -> str:
    """Serialize an AgentOp tree to JSON (code -> data)."""
    return json.dumps(op, indent=indent, default=str)


def from_json(json_str: str) -> AgentOp:
    """Deserialize JSON to an AgentOp tree (data -> code)."""
    return json.loads(json_str)


# -----------------------------------------------------------
# S6 - Tree Introspection (Python-side)
# -----------------------------------------------------------


def node_count(op: AgentOp) -> int:
    """Count all nodes in the dispatch tree."""
    if isinstance(op, str):
        return 1  # Noop or simple variant
    if not isinstance(op, dict):
        return 0

    for variant, data in op.items():
        if variant in ("Seq", "Par") and isinstance(data, list):
            return 1 + sum(node_count(child) for child in data)
        if variant == "Cond" and isinstance(data, dict):
            return (
                1
                + node_count(data.get("then_branch", {}))
                + node_count(data.get("else_branch", {}))
            )
        if variant == "Loop" and isinstance(data, dict):
            return 1 + node_count(data.get("body", {}))
        if variant == "Rewrite" and isinstance(data, dict):
            return 1 + node_count(data.get("replacement", {}))
        return 1
    return 1


def dispatch_targets(op: AgentOp) -> list:
    """Collect all dispatch targets in the tree."""
    targets: list = []
    _collect_targets(op, targets)
    return targets


def _collect_targets(op: AgentOp, targets: list) -> None:
    if isinstance(op, str) or not isinstance(op, dict):
        return
    for variant, data in op.items():
        if variant == "Dispatch" and isinstance(data, dict):
            targets.append(data.get("target", ""))
        elif variant in ("Seq", "Par") and isinstance(data, list):
            for child in data:
                _collect_targets(child, targets)
        elif variant == "Cond" and isinstance(data, dict):
            _collect_targets(data.get("then_branch", {}), targets)
            _collect_targets(data.get("else_branch", {}), targets)
        elif variant == "Loop" and isinstance(data, dict):
            _collect_targets(data.get("body", {}), targets)
        elif variant == "Rewrite" and isinstance(data, dict):
            _collect_targets(data.get("replacement", {}), targets)
