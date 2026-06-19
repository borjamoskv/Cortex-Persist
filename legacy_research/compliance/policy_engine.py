# [C5-REAL] Exergy-Maximized
"""PolicyEngine - Admission controller and runtime policy validation for agent governance."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.compliance.policy_engine")

DEFAULT_POLICY_PATH = Path("~/.cortex/comply_policies.json").expanduser()

DEFAULT_POLICIES = {
    "roles": {
        "admin": ["*"],
        "writer": ["read", "write"],
        "reader": ["read"],
        "k0-daemon": ["read", "write", "execute"],
        "swarm-agent": ["read", "write"]
    },
    "agent_assignments": {
        "agent:unknown": "reader",
        "agent:k0": "k0-daemon",
        "agent:swarm": "swarm-agent"
    },
    "limits": {
        "max_cost_per_tx": 0.50,  # USD or Exergy Joules threshold
        "max_error_rate": 0.25,   # Suspension threshold
        "max_queue_depth": 50     # Overload threshold
    }
}


class PolicyEngine:
    """Evaluates agent actions against RBAC rules and dynamic operational bounds."""

    def __init__(self, policy_path: str | Path = DEFAULT_POLICY_PATH) -> None:
        self.policy_path = Path(policy_path)
        self.policies = self._load_policies()

    def _load_policies(self) -> dict[str, Any]:
        if self.policy_path.exists():
            try:
                with open(self.policy_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load policy file {self.policy_path}: {e}. Using defaults.")
        
        # Save defaults if no file exists
        self._save_policies(DEFAULT_POLICIES)
        return DEFAULT_POLICIES

    def _save_policies(self, data: dict[str, Any]) -> None:
        try:
            self.policy_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.policy_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save policy file {self.policy_path}: {e}")

    def evaluate_action(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """Evaluate if an agent is authorized to perform an action on a resource given the context.

        Returns (is_allowed, reason).
        """
        context = context or {}
        
        # 1. RBAC Evaluation
        role = self.policies.get("agent_assignments", {}).get(agent_id, "reader")
        allowed_actions = self.policies.get("roles", {}).get(role, [])

        if "*" not in allowed_actions and action not in allowed_actions:
            return False, f"Agent {agent_id} with role {role} is unauthorized for action '{action}' on resource '{resource}'."

        # 2. Dynamic limit evaluations (Budget / Costs)
        limits = self.policies.get("limits", {})
        
        if "cost" in context:
            cost = float(context["cost"])
            max_cost = float(limits.get("max_cost_per_tx", 0.50))
            if cost > max_cost:
                return False, f"Action cost {cost} exceeds the configured limit of {max_cost} per transaction."

        if "error_rate" in context:
            error_rate = float(context["error_rate"])
            max_error_rate = float(limits.get("max_error_rate", 0.25))
            if error_rate > max_error_rate:
                return False, f"Agent error rate {error_rate} exceeds limit {max_error_rate}. Agent execution throttled/suspended."

        if "queue_depth" in context:
            queue_depth = int(context["queue_depth"])
            max_queue_depth = int(limits.get("max_queue_depth", 50))
            if queue_depth > max_queue_depth:
                return False, f"Agent queue depth {queue_depth} exceeds limit {max_queue_depth}. Core overloaded."

        return True, "Action approved by policy engine."

    def assign_role(self, agent_id: str, role: str) -> None:
        """Assign a compliance role to an agent."""
        if role not in self.policies.get("roles", {}):
            raise ValueError(f"Role {role} is not defined in policies.")
        self.policies.setdefault("agent_assignments", {})[agent_id] = role
        self._save_policies(self.policies)
