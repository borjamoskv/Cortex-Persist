"""
Enterprise RBAC Guard.
Intercepts operations to ensure they possess a valid SovereignIdentity
and the required scopes before allowing state mutation or persistence.
"""

from typing import Any, Dict

from cortex.auth.enterprise_identity import SovereignIdentity, TenantRBAC

class EnterpriseRBACGuard:
    """
    Guard that enforces Tenant RBAC at the boundary of the Semantic CRDT
    or the distributed memory bus.
    """

    def __init__(self, require_explicit_identity: bool = True):
        self.require_explicit_identity = require_explicit_identity

    def validate_proposal(self, identity: SovereignIdentity, action: str, resource: str, payload: Dict[str, Any]) -> bool:
        """
        Validates if the provided identity can execute the proposed action on the resource.
        
        Args:
            identity: The SovereignIdentity requesting the action.
            action: The operation being attempted (e.g., 'crdt:write_volatile', 'ledger:append').
            resource: The URI or identifier of the resource.
            payload: The data associated with the action.
            
        Returns:
            True if authorized.
            
        Raises:
            PermissionError: If the identity lacks the required scopes.
        """
        if self.require_explicit_identity and not identity:
            raise PermissionError("Enterprise BFT requires a signed SovereignIdentity.")

        if not TenantRBAC.validate_action(identity, action):
            raise PermissionError(
                f"SovereignIdentity '{identity.actor_id}' (Role: {identity.role}) "
                f"lacks scope '{action}' required to access resource '{resource}'."
            )

        # In a fully deployed BFT cluster, here we would also verify the identity signature
        # against the tenant's public key registry.
        
        return True
