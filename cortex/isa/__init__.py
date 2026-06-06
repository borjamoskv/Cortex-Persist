# [C5-REAL] Exergy-Maximized
"""CORTEX Agent ISA - Python DSL for Code-as-Data dispatch trees.

Homoiconic builder: constructs AgentOp trees in Python that execute
entirely in Rust via zero-copy PyO3 FFI. Python only builds the plan;
the hot loop never crosses the FFI boundary.

Reality Level: C5-REAL
"""

from cortex.isa.builder import (
    AgentOp,
    HaltReason,
    LedgerMutation,
    LedgerQuery,
    MutationOp,
    Predicate,
    Ref,
    SelfQuery,
    bind,
    cond,
    # Builder DSL shortcuts
    dispatch,
    dispatch_targets,
    from_json,
    halt,
    loop_n,
    mutate,
    # Introspection
    node_count,
    noop,
    par,
    query,
    reflect,
    rewrite,
    seq,
    # Serialization
    to_json,
    transform,
)

__all__ = [
    "AgentOp",
    "HaltReason",
    "LedgerMutation",
    "LedgerQuery",
    "MutationOp",
    "Predicate",
    "Ref",
    "SelfQuery",
    "bind",
    "cond",
    "dispatch",
    "dispatch_targets",
    "from_json",
    "halt",
    "loop_n",
    "mutate",
    "node_count",
    "noop",
    "par",
    "query",
    "reflect",
    "rewrite",
    "seq",
    "to_json",
    "transform",
]
