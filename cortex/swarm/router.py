from __future__ import annotations

import copy
import hashlib
import json

from cortex.swarm.graph_source import GraphSource
from cortex.swarm.ledger.engine import SwarmLedger
from cortex.swarm.ledger.models import SwarmEvent


class SwarmRouter:
    """
    Routes requests using either:
      1. SNGraphSource  — SN subgraph drives candidate selection (neural mode)
      2. registry       — classic registry fallback

    In both cases every decision is appended to SwarmLedger.
    _dispatch() is a pure function: no side effects, no self state reads.
    """

    def __init__(self, registry, graph_source: GraphSource | None = None):
        self.registry = registry
        self.graph_source = graph_source
        self.ledger = SwarmLedger()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, request: dict) -> dict:
        if self.graph_source is not None:
            raw_candidates = self.graph_source.get_candidates(request["task"])
            candidates = [c.to_dict() for c in raw_candidates]
            registry_snapshot = self._frozen_snapshot()
        else:
            if hasattr(self.registry, "_frozen") and not self.registry._frozen:
                self.registry.freeze()
            raw_candidates = sorted(
                self.registry.get_candidates(request.get("task", "")),
                key=lambda a: getattr(a, "agent_id", getattr(a, "name", str(a))),
            )
            # Ensure agent_id is populated from name if missing
            candidates = []
            for a in raw_candidates:
                if hasattr(a, "__dict__"):
                    d = dict(a.__dict__)
                    d.setdefault("agent_id", d.get("name", str(a)))
                    candidates.append(d)
                elif isinstance(a, dict):
                    candidates.append(a)
                else:
                    candidates.append({"agent_id": str(a)})

            if not candidates:
                # Fallback to all agents sorted
                all_agents = sorted(
                    self.registry.all(),
                    key=lambda a: getattr(a, "agent_id", getattr(a, "name", str(a))),
                )
                for a in all_agents:
                    if hasattr(a, "__dict__"):
                        d = dict(a.__dict__)
                        d.setdefault("agent_id", d.get("name", str(a)))
                        candidates.append(d)
                    else:
                        candidates.append({"agent_id": str(a)})
            registry_snapshot = self._frozen_snapshot()

        entropy_score = _evaluate_entropy(request)
        selected = _dispatch(candidates, request, entropy_score)

        # Serialize capabilities to sorted list for JSON stability
        for k, v in selected.items():
            if isinstance(v, (set, frozenset)):
                selected[k] = sorted(list(v))

        # Filter out unserializable objects before hashing
        safe_selected = _deep_sorted({k: v for k, v in selected.items() if not k.startswith("_")})

        state_str = json.dumps(safe_selected, sort_keys=True)
        routing_hash = hashlib.sha256(state_str.encode()).hexdigest()
        selected["routing_hash"] = routing_hash

        selected_agent = selected.get("agent_id", "unknown")

        self.ledger.append(
            SwarmEvent(
                task=request.get("task", ""),
                input=copy.deepcopy(request),
                registry_state=registry_snapshot,
                selected_agent=selected_agent,
                routing_payload=selected,
                quorum_agents=selected.get("quorum_agents"),
                entropy_score=entropy_score,
            )
        )

        return selected

    def registry_checksum(self) -> str:
        """Stable hash of the registry configuration."""
        snap = self._frozen_snapshot()
        state_str = json.dumps(snap, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _frozen_snapshot(self) -> dict:
        """Deep-frozen, sorted snapshot of registry state."""
        if hasattr(self.registry, "snapshot"):
            raw = self.registry.snapshot()
        elif hasattr(self.registry, "to_dict"):
            raw = self.registry.to_dict()
        else:
            raw = {}
        return _deep_sorted(copy.deepcopy(raw))


# ------------------------------------------------------------------
# Pure functions  (no self, no side-effects)
# ------------------------------------------------------------------


def _evaluate_entropy(request: dict) -> float:
    """
    Thermodynamic evaluation of task complexity.
    Returns a score between 0.0 and 1.0.
    """
    task = request.get("task", "")
    score = 0.1
    # Simple structural heuristic for high entropy
    if len(task) > 100:
        score += 0.3
    if any(k in task.lower() for k in ["refactor", "research", "architecture", "consensus", "byzantine", "deep"]):
        score += 0.4
    if request.get("force_quorum", False):
        score = 1.0
    return min(1.0, score)


def _dispatch(candidates: list[dict], request: dict, entropy_score: float) -> dict:
    """Pure selection: assigns to Quorum if high entropy, else single agent."""
    if not candidates:
        raise ValueError(f"No candidates for task: {request.get('task', '')}")

    selected_agents = sorted([c.get("agent_id") for c in candidates if "agent_id" in c])

    if entropy_score >= 0.5 and len(candidates) >= 3:
        # ZK-Swarm Consensus: dispatch to Quorum (N=3)
        quorum = candidates[:3]
        quorum_ids = [c.get("agent_id", "unknown") for c in quorum]
        payload = {
            "agent_id": "quorum_consensus",
            "quorum_agents": quorum_ids,
            "selected_agents": selected_agents,
            "entropy_score": entropy_score,
        }
        # Merge traits from the first candidate as a baseline representation
        for k, v in quorum[0].items():
            if k not in payload:
                payload[k] = v
        return payload
    else:
        # Linear Execution: dispatch to N=1
        payload = {
            "agent_id": candidates[0].get("agent_id", "unknown"),
            "quorum_agents": None,
            "selected_agents": selected_agents,
            "entropy_score": entropy_score,
        }
        payload.update(candidates[0])
        return payload


def _deep_sorted(obj):
    """Recursively sort dict keys for deterministic hashing."""
    if isinstance(obj, dict):
        return {k: _deep_sorted(v) for k, v in sorted(obj.items()) if _is_json_serializable(v)}
    if isinstance(obj, list):
        return [_deep_sorted(i) for i in obj if _is_json_serializable(i)]
    if isinstance(obj, set) or isinstance(obj, frozenset):
        return sorted([_deep_sorted(i) for i in obj])
    return obj


def _is_json_serializable(v):
    try:
        json.dumps(v)
        return True
    except (TypeError, OverflowError):
        return False
