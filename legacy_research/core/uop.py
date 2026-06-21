from dataclasses import dataclass
from typing import Any

from .manifold import _hash_to_vector


@dataclass
class UnknownCore:
    region: str
    unsat_trace: list
    entropy_signature: float
    collapse_vector: list[float]


def make_node(op: str, value: Any, weight: float = 1.0) -> dict[str, Any]:
    return {"op": op, "value": value, "weight": weight}


def extract_unknown_core(event: Any) -> UnknownCore:
    trace = event.z3_trace or {}
    return UnknownCore(
        region=trace.get("region", "void"),
        unsat_trace=trace.get("unsat_core", []),
        entropy_signature=event.entropy_signature,
        collapse_vector=_hash_to_vector(trace),
    )


def synthesize_ast_from_collapse(core: UnknownCore) -> list[dict[str, Any]]:
    ast = []

    # 1. seed from unsat constraints
    for constraint in core.unsat_trace:
        ast.append(make_node("residual_constraint", constraint, core.entropy_signature))

    # 2. inject collapse geometry
    ast.append(make_node("collapse_vector_anchor", core.collapse_vector))

    # 3. latent mutation nodes
    if core.entropy_signature > 0.7:
        ast.append(make_node("ghost_branch", "UNRESOLVED_PATH"))

    return ast


def unknown_as_operator(retrieval_event: Any) -> list[dict[str, Any]] | None:
    state_val = (
        retrieval_event.state.value
        if hasattr(retrieval_event.state, "value")
        else str(retrieval_event.state)
    )
    if state_val not in ["unknown", "undecidable", "solver-silent"]:
        return None

    core = extract_unknown_core(retrieval_event)
    return synthesize_ast_from_collapse(core)
