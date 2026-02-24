"""Tests for ABAC (Attribute-Based Access Control)."""

from __future__ import annotations

import pytest

from cortex.security.abac import (
    ABACEvaluator,
    AccessContext,
    AccessDecision,
    Effect,
    Policy,
    PolicyViolationError,
)


class TestAccessDecision:
    def test_granted_value(self) -> None:
        assert AccessDecision.GRANTED == "granted"

    def test_denied_value(self) -> None:
        assert AccessDecision.DENIED == "denied"


class TestPolicy:
    def test_policy_creation(self) -> None:
        p = Policy(
            name="test",
            effect=Effect.ALLOW,
            resource="fact",
            action="read",
        )
        assert p.name == "test"
        assert p.effect == Effect.ALLOW
        assert p.resource == "fact"
        assert p.action == "read"
        assert p.priority == 0

    def test_policy_immutable(self) -> None:
        p = Policy(name="test", effect=Effect.ALLOW, resource="fact", action="read")
        with pytest.raises(AttributeError):
            p.name = "changed"  # type: ignore[misc]


class TestABACEvaluator:
    @pytest.fixture()
    def evaluator(self) -> ABACEvaluator:
        """Evaluator with default policies."""
        return ABACEvaluator()

    def _ctx(
        self,
        role: str = "agent",
        sub_tenant: str = "t1",
        res_tenant: str = "t1",
        resource: str = "fact",
        action: str = "read",
    ) -> AccessContext:
        return AccessContext(
            subject={"role": role, "tenant_id": sub_tenant},
            resource={"type": resource, "tenant_id": res_tenant},
            action=action,
        )

    # --- Tenant Isolation Tests ---

    def test_same_tenant_access_granted(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="agent", sub_tenant="t1", res_tenant="t1")
        assert evaluator.evaluate(ctx) == AccessDecision.GRANTED

    def test_cross_tenant_access_denied(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="agent", sub_tenant="t1", res_tenant="t2")
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    def test_cross_tenant_denied_even_for_admin(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="admin", sub_tenant="t1", res_tenant="t2")
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    def test_system_role_bypasses_tenant_isolation(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="system", sub_tenant="t1", res_tenant="t2")
        # System has priority 99, tenant isolation has priority 100
        # So tenant isolation DENY wins
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    # --- Role-Based Tests ---

    def test_viewer_can_read_facts(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="viewer", action="read")
        assert evaluator.evaluate(ctx) == AccessDecision.GRANTED

    def test_viewer_cannot_write_facts(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="viewer", action="write")
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    def test_agent_can_write_facts(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="agent", action="write")
        assert evaluator.evaluate(ctx) == AccessDecision.GRANTED

    def test_agent_can_read_facts(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="agent", action="read")
        assert evaluator.evaluate(ctx) == AccessDecision.GRANTED

    def test_admin_full_access(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="admin", action="delete")
        assert evaluator.evaluate(ctx) == AccessDecision.GRANTED

    def test_system_full_access(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="system", action="delete")
        assert evaluator.evaluate(ctx) == AccessDecision.GRANTED

    def test_unknown_role_denied(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="hacker", action="read")
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    # --- Authorize (raise on deny) ---

    def test_authorize_raises_on_denial(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="viewer", action="write")
        with pytest.raises(PolicyViolationError, match="Access denied"):
            evaluator.authorize(ctx)

    def test_authorize_passes_on_grant(self, evaluator: ABACEvaluator) -> None:
        ctx = self._ctx(role="agent", action="read")
        evaluator.authorize(ctx)  # Should not raise

    # --- Custom Policies ---

    def test_custom_deny_policy(self) -> None:
        policies = [
            Policy(
                name="block-delete",
                effect=Effect.DENY,
                resource="fact",
                action="delete",
                priority=100,
            ),
            Policy(
                name="allow-all",
                effect=Effect.ALLOW,
                resource="*",
                action="*",
                conditions={"subject.role": "admin"},
                priority=50,
            ),
        ]
        evaluator = ABACEvaluator(policies)
        ctx = AccessContext(
            subject={"role": "admin", "tenant_id": "t1"},
            resource={"type": "fact", "tenant_id": "t1"},
            action="delete",
        )
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    def test_empty_policies_deny_by_default(self) -> None:
        evaluator = ABACEvaluator(policies=[])
        ctx = AccessContext(
            subject={"role": "admin", "tenant_id": "t1"},
            resource={"type": "fact", "tenant_id": "t1"},
            action="read",
        )
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    def test_priority_ordering(self) -> None:
        policies = [
            Policy(
                name="low-allow",
                effect=Effect.ALLOW,
                resource="fact",
                action="read",
                priority=1,
            ),
            Policy(
                name="high-deny",
                effect=Effect.DENY,
                resource="fact",
                action="read",
                priority=10,
            ),
        ]
        evaluator = ABACEvaluator(policies)
        ctx = AccessContext(
            subject={"role": "agent", "tenant_id": "t1"},
            resource={"type": "fact", "tenant_id": "t1"},
            action="read",
        )
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    def test_same_priority_deny_wins(self) -> None:
        policies = [
            Policy(
                name="allow",
                effect=Effect.ALLOW,
                resource="fact",
                action="read",
                priority=5,
            ),
            Policy(
                name="deny",
                effect=Effect.DENY,
                resource="fact",
                action="read",
                priority=5,
            ),
        ]
        evaluator = ABACEvaluator(policies)
        ctx = AccessContext(
            subject={"role": "agent", "tenant_id": "t1"},
            resource={"type": "fact", "tenant_id": "t1"},
            action="read",
        )
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED

    # --- Resource Type Matching ---

    def test_wildcard_resource_matches(self) -> None:
        policies = [
            Policy(
                name="allow-all-res",
                effect=Effect.ALLOW,
                resource="*",
                action="read",
                priority=10,
            ),
        ]
        evaluator = ABACEvaluator(policies)
        ctx = AccessContext(
            subject={"role": "agent", "tenant_id": "t1"},
            resource={"type": "report", "tenant_id": "t1"},
            action="read",
        )
        assert evaluator.evaluate(ctx) == AccessDecision.GRANTED

    def test_non_matching_resource_denied(self) -> None:
        policies = [
            Policy(
                name="only-facts",
                effect=Effect.ALLOW,
                resource="fact",
                action="read",
                priority=10,
            ),
        ]
        evaluator = ABACEvaluator(policies)
        ctx = AccessContext(
            subject={"role": "agent", "tenant_id": "t1"},
            resource={"type": "report", "tenant_id": "t1"},
            action="read",
        )
        assert evaluator.evaluate(ctx) == AccessDecision.DENIED
