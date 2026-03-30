import pytest
import os
from cortex.daemon.maxwell import MaxwellDaemon
from cortex.engine.refinement import SovereignRefiner

class MockEngine:
    def __init__(self):
        self.shannon = None

@pytest.fixture
def mock_engine():
    return MockEngine()

def test_maxwell_refinement_trigger(mock_engine):
    daemon = MaxwellDaemon(mock_engine)
    # This should trigger the refiner logic
    ghosts = daemon.trigger_architectural_refinement()
    assert isinstance(ghosts, int)

def test_refiner_scan(tmp_path):
    # Create a "Bloated" file in a temp directory
    p = tmp_path / "bloated.py"
    # Create a function with many nodes
    content = "def bloated_func():\n"
    for i in range(100):
        content += f"    x{i} = {i}\n"
    p.write_text(content)

    refiner = SovereignRefiner(str(tmp_path))
    ghosts = refiner.scan_for_ghosts()
    
    # It should detect the bloated function
    assert any(g["type"] == "BloatedFunction" for g in ghosts)
    assert any("bloated_func" in g["name"] for g in ghosts)
