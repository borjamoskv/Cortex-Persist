import pytest
from cortex.engine.reversible_ledger import ReversibleLedger

def test_reversible_ledger_zero_erasure_h_reversible_01():
    ledger = ReversibleLedger()
    
    # 1. ASSERT (Inyección de Conocimiento)
    fact_1 = ledger.assert_fact("El núcleo de la Tierra es de hierro líquido.")
    fact_2 = ledger.assert_fact("El framework frontend es React.")
    
    # El estado actual debe tener 2 hechos
    state_initial = ledger.resolve_current_state()
    assert len(state_initial) == 2
    assert state_initial[fact_1] == "El núcleo de la Tierra es de hierro líquido."
    assert state_initial[fact_2] == "El framework frontend es React."
    
    # 2. INVERT (Depreciación Destructiva Reemplazada)
    # H-REVERSIBLE-01: No borramos el byte de la RAM/Disco, anexamos el inverso.
    inversion_id = ledger.deprecate_fact(fact_2)
    
    # 3. VERIFICACIÓN ESTRUCTURAL (Resolución Colapsada)
    state_final = ledger.resolve_current_state()
    assert len(state_final) == 1
    assert fact_1 in state_final
    assert fact_2 not in state_final  # El hecho está lógicamente inactivo
    
    # 4. VERIFICACIÓN TERMODINÁMICA (Trazabilidad Causal Pura)
    # El historial completo no ha perdido entropía, sigue intacto (Zero Erasure).
    lineage = ledger.get_full_lineage()
    assert len(lineage) == 3
    
    # Validamos que el Delta 3 es la inversión del Delta 2
    assert lineage[2].action == "INVERT"
    assert lineage[2].causal_parent == fact_2
    assert lineage[2].fact_id == inversion_id
    
def test_reversible_ledger_prevents_invalid_inversion():
    ledger = ReversibleLedger()
    with pytest.raises(ValueError, match="no encontrado"):
        ledger.deprecate_fact("hash_falso_inexistente")
