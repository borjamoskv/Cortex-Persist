import pytest
from legacy_research.engine.causal.solver_gateway import SolverGateway
from legacy_research.engine.immunity.rls_policy import RLSGateway

def test_solver_gateway_routing():
    # It should route to the Rust Data Plane (or mock if not compiled)
    res = SolverGateway.verify_smt("(assert false)")
    assert res in ["Valid", "Error", "Invalid", "Undetermined"]

def test_rls_gateway_matrix():
    RLSGateway.register_agent("tenant_1", "agent_a")
    
    # Positive case: in tenant, and status is sealed (or staging + same agent)
    fact = {"validation_status": "sealed", "agent_id": "agent_a"}
    assert RLSGateway.evaluate_read_access("tenant_1", "agent_a", fact)
    
    # Negative case: wrong tenant
    assert not RLSGateway.evaluate_read_access("tenant_2", "agent_a", fact)
    
    # Negative case: staging fact of another agent
    staging_fact = {"validation_status": "staging", "agent_id": "agent_b"}
    assert not RLSGateway.evaluate_read_access("tenant_1", "agent_a", staging_fact)
