from cortex.swarm.ledger.engine import SwarmLedger
from cortex.swarm.ledger.models import SwarmEvent


class SwarmRouter:
    def __init__(self, registry):
        self.registry = registry
        self.ledger = SwarmLedger()

    def registry_checksum(self) -> str:
        """Stable hash of the registry configuration."""
        import json, hashlib
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

        self.ledger.append(
            SwarmEvent(
                task=request["task"],
                input=request,
                registry_state=self.registry.to_dict(),
                selected_agent=selected["agent_id"],
                routing_payload=selected,
            )
        )

        return selected

    def _dispatch(self, candidates: list, request: dict) -> dict:
        """Pure function: deterministic selection from sorted candidates."""
        if not candidates:
            raise ValueError(f"No candidates for task: {request['task']}")
        # Deterministic: first by agent_id (already sorted)
        return {"agent_id": candidates[0].agent_id, **getattr(candidates[0], '__dict__', {})}
