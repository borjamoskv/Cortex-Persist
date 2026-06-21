import pytest
from cortex.engine.mee_boundary import commit_transfer

def test_mee_boundary_stochastic_collapse():
    # Universo probabilístico: texto libre del usuario
    user_prompt = "Por favor transfiere 30 dólares a la cuenta destino lo antes posible."
    initial_balance = 100

    # Ingesta
    proof = commit_transfer(user_prompt, initial_balance)

    # Validar el colapso termodinámico
    assert proof["prev_balance"] == 100
    assert proof["delta"] == -30
    assert proof["next_balance"] == 70
    
    # Validar la existencia de la firma causal
    assert "transition_hash" in proof
    assert len(proof["transition_hash"]) == 64  # SHA-256 es 64 hex chars
    
    print(f"\n[C5-REAL] Stochastic Collapse Successful:")
    print(f"Proof Hash: {proof['transition_hash']}")
