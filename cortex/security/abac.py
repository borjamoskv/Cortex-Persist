"""
CORTEX v8 — Attribute-Based Access Control (ABAC).

Fine-grained policy engine layered on top of RBAC.
Evaluates access based on subject attributes (role, tenant_id),
resource attributes (project, fact_type), and environmental context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "ABACEvaluator",
    "AccessDecision",
    "Effect",
    "Policy",
    "PolicyViolationError",
]

logger = logging.getLogger("cortex.security.abac")

# Attribute constants for policy conditions
ATTR_SUBJECT_ROLE = "subject.role"


class Effect(str, Enum):
    """Policy effect — explicitly allow or deny."""

    ALLOW = "allow"
    DENY = "deny"


class AccessDecision(str, Enum):
    """Final access decision after policy evaluation."""

    GRANTED = "granted"
    DENIED = "denied"


class PolicyViolationError(Exception):
    """Raised when ABAC denies access."""


@dataclass(frozen=True, slots=True)
class Policy:
    """An ABAC policy rule.

    Attributes:
        name: Human-readable policy name.
        effect: ALLOW or DENY.
        resource: Resource type (e.g., "fact", "compliance_report", "*").
        action: Action type (e.g., "read", "write", "delete", "*").
        conditions: Dict of attribute conditions to match.
            Keys are dot-paths like "subject.tenant_id" or "resource.project".
            Values are the expected values (or "*" for any).
        priority: Higher priority policies take precedence (default 0).
    """

    name: str
    effect: Effect
    resource: str
    action: str
    conditions: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


# Default policies — deny-by-default, then layer allows
DEFAULT_POLICIES: list[Policy] = [
    # Tenant isolation: users can only access their own tenant's data
    Policy(
        name="tenant-isolation",
        effect=Effect.DENY,
        resource="*",
        action="*",
        conditions={"subject.tenant_id": "__MISMATCH__"},
        priority=100,
    ),
    # Viewers can read facts
    Policy(
        name="viewer-read-facts",
        effect=Effect.ALLOW,
        resource="fact",
        action="read",
        conditions={ATTR_SUBJECT_ROLE: "viewer"},
        priority=10,
    ),
    # Agents can read and write facts
    Policy(
        name="agent-write-facts",
        effect=Effect.ALLOW,
        resource="fact",
        action="write",
        conditions={ATTR_SUBJECT_ROLE: "agent"},
        priority=10,
    ),
    Policy(
        name="agent-read-facts",
        effect=Effect.ALLOW,
        resource="fact",
        action="read",
        conditions={ATTR_SUBJECT_ROLE: "agent"},
        priority=10,
    ),
    # Admins can do everything
    Policy(
        name="admin-full-access",
        effect=Effect.ALLOW,
        resource="*",
        action="*",
        conditions={ATTR_SUBJECT_ROLE: "admin"},
        priority=50,
    ),
    # System role: unrestricted
    Policy(
        name="system-unrestricted",
        effect=Effect.ALLOW,
        resource="*",
        action="*",
        conditions={ATTR_SUBJECT_ROLE: "system"},
        priority=99,
    ),
]


@dataclass
class AccessContext:
    """Context for an access request."""

    subject: dict[str, Any]  # {"role": "agent", "tenant_id": "t1", "user_id": "u1"}
    resource: dict[str, Any]  # {"type": "fact", "project": "p1", "tenant_id": "t1"}
    action: str  # "read", "write", "delete"
    environment: dict[str, Any] = field(default_factory=dict)  # optional metadata


class ABACEvaluator:
    """Attribute-Based Access Control evaluator.

    Evaluates policies in priority order. Deny takes precedence over Allow
    at the same priority level (deny-by-default).
    """

    def __init__(self, policies: list[Policy] | None = None) -> None:
        raw = DEFAULT_POLICIES if policies is None else policies
        self._policies = sorted(
            raw,
            key=lambda p: p.priority,
            reverse=True,  # highest priority first
        )

    def evaluate(self, ctx: AccessContext) -> AccessDecision:
        """Evaluate all matching policies and return a final decision.

        Args:
            ctx: The access context describing who, what, and how.

        Returns:
            AccessDecision.GRANTED or AccessDecision.DENIED.
        """
        applicable: list[Policy] = []

        for policy in self._policies:
            if self._matches(policy, ctx):
                applicable.append(policy)

        if not applicable:
            logger.debug("No policies matched — deny by default")
            return AccessDecision.DENIED

        # Among applicable, highest priority wins. If tied, DENY wins.
        top_priority = applicable[0].priority
        top_policies = [p for p in applicable if p.priority == top_priority]

        for p in top_policies:
            if p.effect == Effect.DENY:
                logger.info("Access DENIED by policy '%s'", p.name)
                return AccessDecision.DENIED

        # All top-priority policies are ALLOW
        logger.debug("Access GRANTED by policy '%s'", top_policies[0].name)
        return AccessDecision.GRANTED

    def authorize(self, ctx: AccessContext) -> None:
        """Evaluate and raise PolicyViolationError if denied."""
        decision = self.evaluate(ctx)
        if decision == AccessDecision.DENIED:
            raise PolicyViolationError(
                f"Access denied: {ctx.action} on {ctx.resource.get('type', '?')} "
                f"for role={ctx.subject.get('role', '?')} "
                f"tenant={ctx.subject.get('tenant_id', '?')}"
            )

    def _matches(self, policy: Policy, ctx: AccessContext) -> bool:
        """Check if a policy applies to the given context."""
        if not self._match_resource_and_action(policy, ctx):
            return False
        return self._match_conditions(policy, ctx)

    def _match_resource_and_action(self, policy: Policy, ctx: AccessContext) -> bool:
        if policy.resource != "*" and policy.resource != ctx.resource.get("type"):
            return False
        if policy.action != "*" and policy.action != ctx.action:
            return False
        return True

    def _match_conditions(self, policy: Policy, ctx: AccessContext) -> bool:
        for key, expected in policy.conditions.items():
            if not self._match_single_condition(key, expected, ctx):
                return False
        return True

    def _match_single_condition(self, key: str, expected: Any, ctx: AccessContext) -> bool:
        actual = self._resolve_attribute(key, ctx)

        # Special: tenant isolation check
        if expected == "__MISMATCH__":
            sub_tenant = ctx.subject.get("tenant_id")
            res_tenant = ctx.resource.get("tenant_id")
            if sub_tenant and res_tenant and sub_tenant != res_tenant:
                return True  # Condition matches → this DENY policy applies
            return False

        if expected != "*" and actual != expected:
            return False

        return True

    @staticmethod
    def _resolve_attribute(key: str, ctx: AccessContext) -> Any:
        """Resolve a dot-path attribute from the access context.

        Supports: subject.X, resource.X, environment.X
        """
        parts = key.split(".", 1)
        if len(parts) != 2:
            return None

        namespace, attr = parts
        source = {
            "subject": ctx.subject,
            "resource": ctx.resource,
            "environment": ctx.environment,
        }.get(namespace)

        if source is None:
            return None
        return source.get(attr)


# Global evaluator instance
ABAC = ABACEvaluator()
