import pytest
from babylon60.engine.maxwells_demon import MaxwellsDemon

@pytest.fixture
def demon():
    return MaxwellsDemon()

def test_demon_purges_high_entropy_conversational_text(demon):
    input_text = "Hola, claro que si. Aqui tienes el código que me pediste. Espero que te sea util. Lo siento si hay un error."
    output_text, purge_ratio = demon.filter_context(input_text)
    
    # Debe haber purgado casi todo el teatro verde
    assert "Hola" not in output_text
    assert "claro que si" not in output_text
    assert "Aqui tienes" not in output_text
    assert "Espero que" not in output_text
    assert "Lo siento" not in output_text
    assert purge_ratio > 40.0 # Porcentaje sustancial de purga

def test_demon_preserves_c5_real_exergy_code(demon):
    input_text = "Hola! Aqui tienes la solucion.\n```python\ndef foo():\n    return 42\n```\nEspero que te sirva."
    output_text, purge_ratio = demon.filter_context(input_text)
    
    # El teatro verde desaparece, el código queda intacto.
    assert "Hola" not in output_text
    assert "```python\ndef foo():\n    return 42\n```" in output_text
    assert len(output_text.split()) < len(input_text.split())
    assert purge_ratio > 35.0 # H-THERMO-01: reduce API token consumption by >35%

def test_demon_preserves_structural_yaml_json(demon):
    input_text = "Disculpa la tardanza. La configuración es:\n{\"key\": \"value\", \"exergy\": 100}\nTen en cuenta que esto es crítico."
    output_text, purge_ratio = demon.filter_context(input_text)
    
    assert "{\"key\": \"value\", \"exergy\": 100}" in output_text
    assert "Disculpa" not in output_text
    assert "Ten en cuenta que" not in output_text

def test_demon_handles_pure_entropy_empty_state(demon):
    input_text = ""
    output_text, purge_ratio = demon.filter_context(input_text)
    assert output_text == ""
    assert purge_ratio == 0.0
