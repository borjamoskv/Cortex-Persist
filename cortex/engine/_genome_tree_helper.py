# [C5-REAL] Exergy-Maximized
"""Tree manipulation helper functions for StrategyGenome.

Reality Level: C5-REAL
"""

from __future__ import annotations

from cortex.isa.builder import AgentOp


def replace_target(tree: AgentOp, old_target: str, new_target: str) -> AgentOp:
    """Replace a dispatch target in the tree."""
    if isinstance(tree, str) or not isinstance(tree, dict):
        return tree

    result = {}
    for variant, data in tree.items():
        if variant == "Dispatch" and isinstance(data, dict):
            if data.get("target") == old_target:
                if isinstance(new_target, dict):
                    return new_target
                result[variant] = {**data, "target": new_target}
            else:
                result[variant] = data
        elif variant in ("Seq", "Par") and isinstance(data, list):
            result[variant] = [replace_target(child, old_target, new_target) for child in data]
        elif variant == "Cond" and isinstance(data, dict):
            result[variant] = {
                "predicate": data.get("predicate"),
                "then_branch": replace_target(data.get("then_branch", {}), old_target, new_target),
                "else_branch": replace_target(
                    data.get("else_branch", "Noop"), old_target, new_target
                ),
            }
        elif variant == "Loop" and isinstance(data, dict):
            result[variant] = {
                "count": data.get("count", 1),
                "body": replace_target(data.get("body", {}), old_target, new_target),
            }
        else:
            result[variant] = data
    return result


def remove_target(tree: AgentOp, target: str) -> AgentOp:
    """Remove a dispatch target from the tree, replacing with Noop."""
    if isinstance(tree, str) or not isinstance(tree, dict):
        return tree

    result = {}
    for variant, data in tree.items():
        if variant == "Dispatch" and isinstance(data, dict):
            if data.get("target") == target:
                return "Noop"  # pyright: ignore[reportReturnType]
            result[variant] = data
        elif variant in ("Seq", "Par") and isinstance(data, list):
            children = [remove_target(child, target) for child in data]
            children = [c for c in children if c != "Noop"]
            if not children:
                return "Noop"  # pyright: ignore[reportReturnType]
            result[variant] = children
        elif variant in ("Cond", "Loop"):
            result[variant] = _process_complex_node(variant, data, target)
        else:
            result[variant] = data
    return result


def _process_complex_node(variant: str, data: dict, target: str) -> dict:
    if variant == "Cond":
        return {
            "predicate": data.get("predicate"),
            "then_branch": remove_target(data.get("then_branch", {}), target),
            "else_branch": remove_target(data.get("else_branch", "Noop"), target),
        }
    elif variant == "Loop":
        return {
            "count": data.get("count", 1),
            "body": remove_target(data.get("body", {}), target),
        }
    return data
