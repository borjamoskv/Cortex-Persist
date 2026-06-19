"""
Enterprise Identity and RBAC Definitions.
"""
from dataclasses import dataclass, field
from typing import Set

@dataclass(frozen=True)
class SovereignIdentity:
    """
    Cryptographically verifiable identity representing a human operator, 
    service account, or autonomous agent within the Enterprise ecosystem.
    """
    tenant_id: str
    actor_id: str
    role: str
    scopes: Set[str] = field(default_factory=set)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "admin:all" in self.scopes

class TenantRBAC:
    """
    Role-Based Access Control validator for Tenant operations.
    """
    
    # Define baseline enterprise scopes
    ROLE_SCOPES = {
        "CRDT_ORCHESTRATOR": {"crdt:compact", "crdt:merge", "ledger:append"},
        "AGENT_WORKER": {"crdt:read", "crdt:write_volatile"},
        "AUDITOR": {"ledger:read", "crdt:read"},
        "ADMIN": {"admin:all"}
    }

    @classmethod
    def validate_action(cls, identity: SovereignIdentity, required_scope: str) -> bool:
        # Check explicit scopes
        if identity.has_scope(required_scope):
            return True
            
        # Check implicit role scopes
        role_scopes = cls.ROLE_SCOPES.get(identity.role.upper(), set())
        if required_scope in role_scopes or "admin:all" in role_scopes:
            return True
            
        return False
