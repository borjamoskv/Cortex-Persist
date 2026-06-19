import pytest
from cortex.auth.enterprise_identity import SovereignIdentity
from cortex.guards.enterprise_guard import EnterpriseRBACGuard

def test_rbac_guard_allow():
    identity = SovereignIdentity(
        tenant_id="acme_corp",
        actor_id="agent_alpha",
        role="CRDT_ORCHESTRATOR"
    )
    guard = EnterpriseRBACGuard()
    
    # CRDT_ORCHESTRATOR role implicitly has "crdt:compact"
    assert guard.validate_proposal(identity, "crdt:compact", "resource:x", {}) == True

def test_rbac_guard_deny():
    identity = SovereignIdentity(
        tenant_id="acme_corp",
        actor_id="agent_worker_1",
        role="AGENT_WORKER"
    )
    guard = EnterpriseRBACGuard()
    
    # AGENT_WORKER should NOT have "ledger:append"
    with pytest.raises(PermissionError) as excinfo:
        guard.validate_proposal(identity, "ledger:append", "resource:x", {})
    assert "lacks scope" in str(excinfo.value)

def test_rbac_guard_admin():
    identity = SovereignIdentity(
        tenant_id="acme_corp",
        actor_id="sys_admin",
        role="ADMIN"
    )
    guard = EnterpriseRBACGuard()
    
    # ADMIN should have access to anything
    assert guard.validate_proposal(identity, "super:destructive:action", "db:main", {}) == True
