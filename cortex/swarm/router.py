from cortex.swarm.ledger.engine import SwarmLedger
from cortex.swarm.ledger.models import SwarmEvent


class SwarmRouter:
    def __init__(self, registry):
        self.registry = registry
        self.ledger = SwarmLedger()

    def route(self, request: dict):
        if not self.registry._frozen:
            self.registry.freeze()

        candidates = sorted(
            self.registry.get_candidates(request["task"]),
            key=lambda a: a.agent_id
        )

        selected = self._dispatch(candidates, request)

        self.ledger.append(
            SwarmEvent(
                task=request["task"],
                input=request,
                registry_state=self.registry.snapshot(),
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
