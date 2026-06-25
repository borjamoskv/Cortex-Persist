# [C5-REAL] Exergy-Maximized
from legacy_research.engine.ultrathink_physics import UltrathinkPhysicsEngine


def test_exergy_yield_calculation():
    """Test the derivation of cognitive exergy."""
    # S_stoc = 15.0, S_det = 120.0, T = 2.0s
    exergy = UltrathinkPhysicsEngine.calculate_exergy_yield(15.0, 120.0, 2.0)
    assert exergy == 52.5  # (120-15)/2 = 52.5

    # Negative Exergy -> Should cap at 0
    negative_exergy = UltrathinkPhysicsEngine.calculate_exergy_yield(200.0, 10.0, 1.0)
    assert negative_exergy == 0.0


def test_blast_radius_measurement():
    """Test the topological depth of an isolated failure graph."""
    deps = {"A": ["B", "C"], "B": ["D"], "C": [], "D": ["E", "F"], "E": [], "F": []}

    # Epicenter A touches all 6 nodes
    assert UltrathinkPhysicsEngine.measure_blast_radius(deps, "A") == 6

    # Epicenter B touches B, D, E, F (4)
    assert UltrathinkPhysicsEngine.measure_blast_radius(deps, "B") == 4

    # Epicenter F touches only F (1)
    assert UltrathinkPhysicsEngine.measure_blast_radius(deps, "F") == 1


def test_ultrathink_authorization():
    """Validates the P0 Horizon decision."""
    # Valid Ultrathink: Exergy > 10, Blast >= 3
    auth, msg = UltrathinkPhysicsEngine.authorize_ultrathink(10.0, 200.0, 5.0, 4)
    assert auth is True
    assert "Authorized" in msg

    # Invalid: small blast radius
    auth, msg = UltrathinkPhysicsEngine.authorize_ultrathink(10.0, 200.0, 5.0, 2)
    assert auth is False
    assert "small" in msg

    # Invalid: Low exergy yield
    auth, msg = UltrathinkPhysicsEngine.authorize_ultrathink(50.0, 60.0, 10.0, 5)
    assert auth is False
    assert "Insufficient" in msg
