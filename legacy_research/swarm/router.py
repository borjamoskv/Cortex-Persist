from __future__ import annotations

import copy
import hashlib
import json

from legacy_research.swarm.graph_source import GraphSource
from legacy_research.swarm.ledger.engine import SwarmLedger
from legacy_research.swarm.ledger.models import SwarmEvent


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
            if hasattr(self.registry, '_frozen') and not self.registry._frozen:
                self.registry.freeze()
            raw_candidates = sorted(
                self.registry.get_candidates(request.get("task", "")),
                key=lambda a: getattr(a, 'agent_id', getattr(a, 'name', str(a)))
            )
            # Ensure agent_id is populated from name if missing
            candidates = []
            for a in raw_candidates:
                if hasattr(a, '__dict__'):
                    d = dict(a.__dict__)
                    d.setdefault("agent_id", d.get("name", str(a)))
                    candidates.append(d)
                elif isinstance(a, dict):
                    candidates.append(a)
                else:
                    candidates.append({"agent_id": str(a)})
                    
            if not candidates:
                # Fallback to all agents sorted
                all_agents = sorted(self.registry.all(), key=lambda a: getattr(a, 'agent_id', getattr(a, 'name', str(a))))
                for a in all_agents:
                    if hasattr(a, '__dict__'):
                        d = dict(a.__dict__)
                        d.setdefault("agent_id", d.get("name", str(a)))
                        candidates.append(d)
                    else:
                        candidates.append({"agent_id": str(a)})
            registry_snapshot = self._frozen_snapshot()

        selected = _dispatch(candidates, request)

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
        if hasattr(self.registry, 'snapshot'):
            raw = self.registry.snapshot()
        elif hasattr(self.registry, 'to_dict'):
            raw = self.registry.to_dict()
        else:
            raw = {}
        return _deep_sorted(copy.deepcopy(raw))


# ------------------------------------------------------------------
# Pure functions  (no self, no side-effects)
# ------------------------------------------------------------------

def _dispatch(candidates: list[dict], request: dict) -> dict:
    """Pure selection: scores candidates based on capability overlap, ties broken by agent_id."""
    if not candidates:
        raise ValueError(f"No candidates for task: {request.get('task', '')}")
    
    task_lower = request.get("task", "").lower()
    
    def score_candidate(c: dict) -> tuple[float, int, str]:
        # Priority 1: Salience (from SN graph, if present)
        salience = c.get("salience", 0.0)
        # Priority 2: Capability match count
        caps = c.get("capabilities", [])
        cap_score = sum(1 for cap in caps if isinstance(cap, str) and cap.lower() in task_lower)
        # Priority 3: Alphabetical tie-breaker
        return (-float(salience), -cap_score, str(c.get("agent_id", "unknown")))
    
    ranked_candidates = sorted(candidates, key=score_candidate)
    selected_agents = [c.get("agent_id") for c in ranked_candidates if "agent_id" in c]
    
    best_candidate = ranked_candidates[0]
    payload = {
        "agent_id": best_candidate.get("agent_id", "unknown"),
        "selected_agents": selected_agents,
        "match_score": -score_candidate(best_candidate)[0]
    }
    payload.update(best_candidate)
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
