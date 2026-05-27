import os
import sys
import pytest
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

from ultramap import UltramapSubstrate, EntropyDeath


@pytest.fixture
def temp_umap_env(tmp_path, monkeypatch):
    """Isolate the ultramap binary path to a temporary directory."""
    test_db_path = tmp_path / "cortex_memory_vsa.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(test_db_path))
    # Note: DB_PATH in ultramap module is evaluated at import time.
    # Therefore, we patch ultramap.DB_PATH directly as well.
    import ultramap

    monkeypatch.setattr(ultramap, "DB_PATH", str(test_db_path))

    # Clean any potential stale files
    bin_path = tmp_path / "ultramap.bin"
    if bin_path.exists():
        os.remove(bin_path)

    yield tmp_path

    # Teardown
    if bin_path.exists():
        try:
            os.remove(bin_path)
        except Exception:
            pass


def test_ultramap_initialization(temp_umap_env):
    """Test that UltramapSubstrate correctly initializes the binary file."""
    capacity = 100
    umap = UltramapSubstrate(capacity=capacity)

    bin_path = temp_umap_env / "ultramap.bin"
    assert bin_path.exists()
    assert bin_path.stat().st_size == capacity * 128

    umap.close()


def test_ultramap_update_and_get(temp_umap_env):
    """Verify that agent positions and states are updated and retrieved correctly."""
    umap = UltramapSubstrate(capacity=10)

    # Test valid update
    success = umap.update_agent_position(
        agent_idx=3, x=12.5, y=-45.2, z=100.8, target="CVE-2026-MINIPLASMA", entropy=0.75
    )
    assert success is True

    # Test retrieve
    state = umap.get_agent_state(3)
    assert state["x"] == pytest.approx(12.5)
    assert state["y"] == pytest.approx(-45.2)
    assert state["z"] == pytest.approx(100.8)
    assert state["target"] == "CVE-2026-MINIPLASMA"
    assert state["entropy"] == pytest.approx(0.75)

    umap.close()


def test_ultramap_out_of_bounds(temp_umap_env):
    """Check boundaries and out-of-bounds handling."""
    umap = UltramapSubstrate(capacity=5)

    # Try updating negative index
    assert umap.update_agent_position(-1, 0, 0, 0, "test", 0.5) is False
    # Try updating index >= capacity
    assert umap.update_agent_position(5, 0, 0, 0, "test", 0.5) is False

    # Try getting negative index
    assert umap.get_agent_state(-1) == {}
    assert umap.get_agent_state(5) == {}

    # Distance calculation out of bounds should raise EntropyDeath
    with pytest.raises(EntropyDeath):
        umap.calculate_exergy_distance(-1, "test")

    with pytest.raises(EntropyDeath):
        umap.calculate_exergy_distance(5, "test")

    umap.close()


def test_ultramap_exergy_distance(temp_umap_env):
    """Test thermodynamic exergy distance calculation."""
    umap = UltramapSubstrate(capacity=10)

    # Set agent 0
    umap.update_agent_position(0, 10.0, 20.0, 30.0, "TARGET_A", 0.5)

    # Distance calculation
    target_hash = "TARGET_DARKPOOL_0x1"
    joules_1 = umap.calculate_exergy_distance(0, target_hash)
    assert joules_1 > 0

    # Higher entropy should result in LESS exergy (Joules) required to exploit/traverse
    umap.update_agent_position(0, 10.0, 20.0, 30.0, "TARGET_A", 0.99)
    joules_2 = umap.calculate_exergy_distance(0, target_hash)
    assert joules_2 < joules_1

    umap.close()
