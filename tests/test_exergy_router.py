import pytest
import time
from cortex_rs import ExergyRouter

def test_exergy_router_accepts_valid_payload():
    router = ExergyRouter()
    
    # Payload sin "slop", "anergy" ni "hallucination"
    router.dispatch("task_1", "This is a strictly determinist C5-REAL output.")
    
    # Damos tiempo al thread de background (Flash) para procesar
    time.sleep(0.1)
    
    # APEX intercept no debe fallar, debe devolver el contenido modificado
    result = router.apex_intercept("task_1")
    assert result is not None
    assert "shadow_accept_This is a strictly determinist C5-REAL output." in result

def test_exergy_router_rejects_hallucinations():
    router = ExergyRouter()
    
    # Payload con "slop" (alucinación simulada)
    router.dispatch("task_2", "This is llm slop.")
    
    time.sleep(0.1)
    
    # APEX intercept debe lanzar ValueError por Epistemic Containment Breach
    with pytest.raises(ValueError) as excinfo:
        router.apex_intercept("task_2")
    
    assert "APEX INTERCEPT P0" in str(excinfo.value)
    assert "Entropy 3600" in str(excinfo.value)
    assert "C4-SIM" in str(excinfo.value)

def test_exergy_router_pending():
    router = ExergyRouter()
    # No dispatch
    result = router.apex_intercept("task_none")
    assert result is None
