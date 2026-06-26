# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
from typing import Any

from cortex.engine.causal.graph import AsyncCausalGraph, CausalGraph, propagate_refutation
from cortex.engine.causal.oracle import AsyncCausalOracle, CausalOracle
from cortex.engine.causality_models import (
    CONFIDENCE_LEVELS,
    EDGE_DERIVED_FROM,
    EDGE_TAINTED_BY,
    EDGE_TRIGGERED_BY,
    EDGE_UPDATED_FROM,
    Confidence,
    EpistemicStatus,
    LedgerEvent,
    TaintReport,
    TaintStatus,
    _downgrade_confidence,
)

__all__ = [
    "EDGE_DERIVED_FROM",
    "EDGE_TAINTED_BY",
    "EDGE_TRIGGERED_BY",
    "EDGE_UPDATED_FROM",
    "AsyncCausalGraph",
    "AsyncCausalOracle",
    "CausalGraph",
    "CausalOracle",
    "Confidence",
    "CONFIDENCE_LEVELS",
    "EpistemicStatus",
    "LedgerEvent",
    "TaintReport",
    "TaintStatus",
    "_downgrade_confidence",
    "link_causality",
    "propagate_refutation",
]


def link_causality(
    meta: dict[str, Any] | None,
    signal_id: int | None,
) -> dict[str, Any]:
    """Attach causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m


def rowless_json(data: dict[str, Any]) -> str:
    return json.dumps(data)
