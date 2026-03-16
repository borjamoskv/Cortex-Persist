"""Taint Propagation Engine — Axiom Ω₁₃ Enforcement.

When a fact_node is invalidated or loses confidence, propagate impact
to descendants and recalculate effective_confidence. Without this,
derived facts float on cadáveres perfumados — structurally elegant,
epistemically corrupt.

Algorithm: BFS from invalidated node.
- Invalidated node → TAINTED, effective_confidence = C1
- Direct children → minimum SUSPECT
- Children with ≥50% TAINTED parents → TAINTED
- Recalculate effective_confidence at every touched node

Enforcement: derived persistence is blocked if taint_status != CLEAN.
"""

from __future__ import annotations

import logging

from cortex.causality.models import (
    CONFIDENCE_ORDER,
    REVERSE_CONFIDENCE_ORDER,
    Confidence,
    FactNode,
    TaintStatus,
)

__all__ = [
    "downgrade_confidence",
    "propagate_taint",
    "recompute_effective_confidence",
]

logger = logging.getLogger("cortex.causality.taint")


def downgrade_confidence(base: Confidence, steps: int) -> Confidence:
    """Degrade confidence by N ordinal steps, clamped to C1.

    Args:
        base: Starting confidence level.
        steps: Number of levels to downgrade (≥0).

    Returns:
        Downgraded confidence. Never below C1.
    """
    value = max(1, CONFIDENCE_ORDER[base] - steps)
    return REVERSE_CONFIDENCE_ORDER[value]


def recompute_effective_confidence(
    node: FactNode,
    graph: dict[str, FactNode],
) -> None:
    """Recalculate effective_confidence based on parent taint states.

    Rules:
    - Invalidated or TAINTED → C1 (floor)
    - Any TAINTED parent → downgrade by 2
    - Any SUSPECT parent → downgrade by 1
    - All parents CLEAN → effective = original
    """
    if node.invalidated or node.taint_status == TaintStatus.TAINTED:
        node.effective_confidence = Confidence.C1
        return

    tainted_parents = sum(
        1
        for parent_id in node.parents
        if parent_id in graph and graph[parent_id].taint_status == TaintStatus.TAINTED
    )
    suspect_parents = sum(
        1
        for parent_id in node.parents
        if parent_id in graph and graph[parent_id].taint_status == TaintStatus.SUSPECT
    )

    if tainted_parents > 0:
        node.effective_confidence = downgrade_confidence(node.confidence, 2)
    elif suspect_parents > 0:
        node.effective_confidence = downgrade_confidence(node.confidence, 1)
    else:
        node.effective_confidence = node.confidence


def propagate_taint(
    start_fact_id: str,
    graph: dict[str, FactNode],
) -> set[str]:
    """Propagate taint from an invalidated fact through the causal DAG.

    BFS traversal. Marks the start node as TAINTED and invalidated,
    then walks all descendants. Children get SUSPECT at minimum;
    children with ≥50% TAINTED parents escalate to TAINTED.

    Args:
        start_fact_id: The fact_id of the node being invalidated.
        graph: The in-memory causal DAG as {fact_id: FactNode}.

    Returns:
        Set of all fact_ids that were touched (taint status changed
        or effective_confidence recalculated).

    Raises:
        KeyError: If start_fact_id is not in the graph.
    """
    if start_fact_id not in graph:
        raise KeyError(f"Unknown fact_id: {start_fact_id}")

    touched: set[str] = set()
    queue: list[str] = [start_fact_id]

    # Mark origin as invalidated + tainted
    start = graph[start_fact_id]
    start.invalidated = True
    start.taint_status = TaintStatus.TAINTED
    start.effective_confidence = Confidence.C1

    while queue:
        current_id = queue.pop(0)
        current = graph[current_id]
        touched.add(current_id)

        for child_id in current.children:
            if child_id not in graph:
                logger.warning(
                    "Causal edge references unknown child %s from %s — skipping",
                    child_id,
                    current_id,
                )
                continue

            child = graph[child_id]

            # Minimum: SUSPECT
            if child.taint_status == TaintStatus.CLEAN:
                child.taint_status = TaintStatus.SUSPECT

            # Escalation: ≥50% tainted parents → TAINTED
            parent_count = len(child.parents)
            if parent_count > 0:
                tainted_parent_count = sum(
                    1
                    for pid in child.parents
                    if pid in graph and graph[pid].taint_status == TaintStatus.TAINTED
                )
                if tainted_parent_count / parent_count >= 0.5:
                    child.taint_status = TaintStatus.TAINTED

            recompute_effective_confidence(child, graph)

            if child_id not in touched:
                queue.append(child_id)

    logger.info(
        "Taint propagated from %s — %d nodes touched",
        start_fact_id,
        len(touched),
    )
    return touched
