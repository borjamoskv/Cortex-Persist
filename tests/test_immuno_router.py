import pytest
from legacy_research.engine.immuno_router import MHCRouter, MicroAgent

@pytest.fixture
def mhc_mesh():
    router = MHCRouter()
    
    # Simular la Expansión Clonal: Agentes híper-específicos registrados
    router.bind_t_cell(MicroAgent(
        name="SQL-Agent",
        antigen_regex=r"\b(sql|database|query|tabla)\b",
        handler=lambda x: "SQL-Agent Executing"
    ))
    
    router.bind_t_cell(MicroAgent(
        name="UI-Agent",
        antigen_regex=r"\b(css|html|frontend|boton)\b",
        handler=lambda x: "UI-Agent Executing"
    ))
    
    return router

def test_mhc_antigen_specific_routing(mhc_mesh):
    # El antígeno "necesito una query sql" debe vincularse determinísticamente a SQL-Agent
    intent = "necesito crear una query sql para los usuarios"
    response = mhc_mesh.expose_and_route(intent)
    
    # Asserting 0 Tokens de ruteo y binding 100% determinista
    assert response == "SQL-Agent Executing"

def test_mhc_antigen_ui_routing(mhc_mesh):
    intent = "alinear el boton con css en el frontend"
    response = mhc_mesh.expose_and_route(intent)
    
    assert response == "UI-Agent Executing"

def test_mhc_apoptosis_unmatched_antigen(mhc_mesh):
    # Un "General LLM" intentaría responder esto, alucinando y gastando tokens.
    # El MHC simplemente rechaza el antígeno al no haber T-Cells compatibles.
    intent = "dime como cocinar una paella valenciana"
    response = mhc_mesh.expose_and_route(intent)
    
    assert "APOPTOSIS" in response
    assert "rechazada" in response
