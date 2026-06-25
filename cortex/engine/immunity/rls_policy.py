# [C5-REAL] Exergy-Maximized
"""
RLS Policy (Control Plane)
Defines the permissions matrix for Retrieval Vaccination.
Determines which identities are allowed to pass through to the Data Plane's
can_read() guardrail in Rust.
"""

import logging

logger = logging.getLogger("cortex.engine.immunity.rls")

class RLSPermissionMatrix:
    """
    Control Plane mapping of tenant and agent relationships.
    Enforces Row-Level Security equivalent in Python before yielding to Rust.
    """
    
    def __init__(self):
        # tenant_id -> list of agent_ids
        self._tenant_agents: dict[str, set[str]] = {}
        
    def register_agent(self, tenant_id: str, agent_id: str):
        if tenant_id not in self._tenant_agents:
            self._tenant_agents[tenant_id] = set()
        self._tenant_agents[tenant_id].add(agent_id)
        
    def can_access_tenant(self, agent_id: str, tenant_id: str) -> bool:
        """
        Verify if the agent belongs to the tenant space.
        If this passes, the Data Plane (Rust) will enforce ValidationStatus.
        """
        return agent_id in self._tenant_agents.get(tenant_id, set())

class RLSGateway:
    """
    SAGA orchestrator integration for read paths.
    """
    
    _matrix = RLSPermissionMatrix()
    
    @classmethod
    def register_agent(cls, tenant_id: str, agent_id: str):
        cls._matrix.register_agent(tenant_id, agent_id)

    @classmethod
    def evaluate_read_access(cls, tenant_id: str, agent_id: str, fact_payload: dict) -> bool:
        """
        1. Control Plane check: Is agent in tenant?
        2. Data Plane check: ValidationStatus visibility (cortex_rs.can_read)
        """
        if not cls._matrix.can_access_tenant(agent_id, tenant_id):
            logger.warning(f"[RLSGateway] Denied: Agent {agent_id} not in Tenant {tenant_id}")
            return False
            
        try:
            import cortex_rs
            if hasattr(cortex_rs, 'retrieval_can_read'):
                # Call Rust native guardrail
                # Assuming FFI mapping: cortex_rs.retrieval_can_read(fact_json_string, agent_id)
                import json
                from cortex_rs import retrieval_can_read  # type: ignore
                return retrieval_can_read(json.dumps(fact_payload), agent_id)
            else:
                # Stub for tests if FFI is not fully linked
                status = fact_payload.get("validation_status", "staging").lower()
                fact_agent = fact_payload.get("agent_id")
                if status == "sealed":
                    return True
                if status == "staging":
                    return agent_id == fact_agent
                return False
        except ImportError:
            logger.error("[RLSGateway] cortex_rs not loaded. Falling back to Python mock check.")
            return False
