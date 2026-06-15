from cortex.swarm.ledger.engine import SwarmLedger
from cortex.swarm.ledger.models import SwarmEvent


class SwarmRouter:
    def __init__(self, registry):
        self.registry = registry
        self.ledger = SwarmLedger()

    def registry_checksum(self) -> str:
        """Stable hash of the registry configuration."""
        import hashlib
        import json
        state_str = json.dumps(self.registry.to_dict(), sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()

    def route(self, request: dict):
        # In V2, registry is naturally deterministic via sorted keys and frozen specs.
        # We find candidates by matching words in task to capabilities, or fallback to all.
        task = request.get("task", "").lower()
        candidates = []
        for agent in self.registry.all():
            if any(cap in task for cap in agent.capabilities):
                candidates.append(agent)
        
        if not candidates:
            # Deterministic fallback: all agents sorted
            candidates = self.registry.all()

        selected = self._dispatch(candidates, request)

        # Serialize capabilities to sorted list for JSON stability
        for k, v in selected.items():
            if isinstance(v, (set, frozenset)):
                selected[k] = sorted(list(v))

        # Generate stable routing_hash
        import hashlib, json
        state_str = json.dumps(selected, sort_keys=True)
        routing_hash = hashlib.sha256(state_str.encode()).hexdigest()
        selected["routing_hash"] = routing_hash

        selected_agent = selected.get("agent_id", "unknown")

        self.ledger.append(
            SwarmEvent(
                task=request["task"],
                input=request,
                registry_state=self.registry.to_dict(),
                selected_agent=selected_agent,
                routing_payload=selected,
            )
        )

        return selected

    def _dispatch(self, candidates: list, request: dict) -> dict:
        """Pure function: deterministic selection from sorted candidates."""
        if not candidates:
            raise ValueError(f"No candidates for task: {request['task']}")
        
        selected_agents = [c.agent_id for c in candidates]
        # Deterministic: first by agent_id (already sorted)
        payload = {
            "agent_id": candidates[0].agent_id,
            "selected_agents": selected_agents
        }
        # Include agent attributes (like capabilities)
        payload.update(getattr(candidates[0], '__dict__', {}))
        return payload
