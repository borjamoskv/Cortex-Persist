import os
import shutil
import tempfile

import pytest

from cortex.extensions.nexus.symlink_engine import SymlinkEngine

@pytest.fixture
def nexus_env():
    # Setup canonical root and satellite
    base_dir = tempfile.mkdtemp()
    canonical_root = os.path.join(base_dir, "CORTEX")
    satellite_root = os.path.join(base_dir, "VAULT")
    
    os.makedirs(canonical_root)
    os.makedirs(satellite_root)
    
    # Create canonical artifacts
    with open(os.path.join(canonical_root, "GEMINI.md"), "w") as f:
        f.write("# Sovereign Rule")
        
    engine = SymlinkEngine(canonical_root)
    
    yield engine, canonical_root, satellite_root
    
    shutil.rmtree(base_dir)

def test_nexus_propagate_symlinks(nexus_env):
    engine, canonical, satellite = nexus_env
    
    # Run propagation
    results = engine.propagate([satellite], ["GEMINI.md"])
    
    assert results[satellite] is True
    
    # Verify symlink exists
    target = os.path.join(satellite, "GEMINI.md")
    assert os.path.islink(target)
    assert os.readlink(target) == os.path.join(canonical, "GEMINI.md")
    
    # Verify invariants
    assert engine.validate_invariants([satellite], ["GEMINI.md"]) is True

def test_nexus_overwrites_physical_redundancy(nexus_env):
    engine, canonical, satellite = nexus_env
    
    # Introduce physical redundancy (Context Rot)
    target = os.path.join(satellite, "GEMINI.md")
    with open(target, "w") as f:
        f.write("# False Rule")
        
    # Invariants should fail initially
    assert engine.validate_invariants([satellite], ["GEMINI.md"]) is False
    
    # Run propagation to purge redundancy
    engine.propagate([satellite], ["GEMINI.md"])
    
    # Verify it became a symlink
    assert os.path.islink(target)
    assert engine.validate_invariants([satellite], ["GEMINI.md"]) is True
