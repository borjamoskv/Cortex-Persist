# [C5-REAL] Exergy-Maximized
import pytest
from legacy_research.engine.entropy import ThermodynamicContextCompressor
from legacy_research.engine.cortex import Cortex

def test_shannon_entropy_calculation():
    # Test blank string yields 0 entropy
    assert ThermodynamicContextCompressor.calculate_shannon_entropy("") == 0.0
    
    # Test structured string shannon entropy
    e_float = ThermodynamicContextCompressor.calculate_shannon_entropy("cortex-persist")
    assert e_float > 0.0
    
    # Test Babylon-60 conversion
    e_b60 = ThermodynamicContextCompressor.calculate_shannon_entropy_b60("cortex-persist")
    assert isinstance(e_b60, Cortex)
    assert e_b60.to_float() == pytest.approx(e_float, abs=1e-4)

def test_thermodynamic_context_compression():
    compressor = ThermodynamicContextCompressor(target_tokens_limit=100)
    
    # Prompt containing Green Theater and narrative fluff
    prompt = """
    Please, could you help me with this task?
    I think maybe the system is broken.
    Here is the code:
    x = 42
    Hope this helps, thank you!
    """
    
    compressed, ratio = compressor.compress_prompt(prompt)
    
    # Fluff lines should be purged
    assert "Please, could you help" not in compressed
    assert "I think maybe the system" not in compressed
    assert "Hope this helps, thank you" not in compressed
    
    # Core lines must be retained
    assert "Here is the code:" in compressed
    assert "x = 42" in compressed
    
    # Check exergy ratio is instance of Cortex
    assert isinstance(ratio, Cortex)
    assert ratio.to_float() < 1.0
    assert ratio.to_float() > 0.0
