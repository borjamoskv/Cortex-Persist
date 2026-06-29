# [C5-REAL] Exergy-Maximized
from cortex.engine.core.ultrathink_physics import UltrathinkPhysicsEngine

import pytest

def test_exergy_yield_calculation():
    """Test the derivation of cognitive exergy."""
    # S_stoc = 15.0, S_det = 120.0, T = 2.0s
    # Thermal penalty (Landauer): 1.05^2 = 1.1025
    # Raw Exergy: (120-15)/2 = 52.5
    # Net Exergy: 52.5 / 1.1025 = 47.619047619
    exergy = UltrathinkPhysicsEngine.calculate_exergy_yield(15.0, 120.0, 2.0)
    assert exergy == pytest.approx(47.6190476, rel=1e-5)

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
    auth, msg, formation = UltrathinkPhysicsEngine.authorize_ultrathink(10.0, 200.0, 5.0, 4)
    assert auth is True
    assert formation is not None
    assert "Authorized" in msg

    # Invalid: small blast radius
    auth, msg, formation = UltrathinkPhysicsEngine.authorize_ultrathink(10.0, 200.0, 5.0, 2)
    assert auth is False
    assert "small" in msg

    # Invalid: Low exergy yield
    auth, msg, formation = UltrathinkPhysicsEngine.authorize_ultrathink(50.0, 60.0, 10.0, 5)
    assert auth is False
    assert "Insufficient" in msg


def test_ultrathink_critical_authorization():
    """Verify that critical domains trigger with lower exergy and blast requirements."""
    # A standard node with blast radius 2 fails
    auth, msg, formation = UltrathinkPhysicsEngine.authorize_ultrathink(10.0, 200.0, 5.0, 2, epicenter_node="ordinary_node")
    assert auth is False

    # A critical node (e.g. "master_ledger") with blast radius 2 succeeds because radius is amplified and exergy threshold is halved
    auth, msg, formation = UltrathinkPhysicsEngine.authorize_ultrathink(10.0, 100.0, 10.0, 2, epicenter_node="master_ledger")
    # exergy = (100 - 10) / 10 = 9.0. Required for critical: 0.05 * 100 = 5.0. 9.0 >= 5.0 -> True.
    # effective_radius = 2 * 1.5 = 3. min_radius = 2 -> True.
    assert auth is True
    assert "Authorized" in msg


def test_exergy_yield_calculation_overflow_handling():
    """Verify that extreme execution times do not trigger OverflowError (VM-03)."""
    # 1.05 ** 10000 will overflow standard floats
    exergy = UltrathinkPhysicsEngine.calculate_exergy_yield(10.0, 100.0, 10000.0)
    assert exergy == 0.0


def test_blast_radius_type_safety():
    """Verify that non-dict graphs are coerced safely (VM-05)."""
    assert UltrathinkPhysicsEngine.measure_blast_radius("not_a_dict", "A") == 1
    # Check sets/tuples are parsed correctly
    deps_with_sets = {"A": {"B", "C"}, "B": ("D",), "C": set()}
    assert UltrathinkPhysicsEngine.measure_blast_radius(deps_with_sets, "A") == 4


def test_ultrathink_arsenal_path_resolution():
    """Verify that SYS_OPERATOR placeholders are resolved dynamically at runtime (VM-04)."""
    from cortex.agents.primitives.ultrathink_arsenal import get_ultrathink_arsenal
    import getpass
    
    current_user = getpass.getuser()
    resolved_directives = get_ultrathink_arsenal()
    
    # Locate a target that originally had SYS_OPERATOR
    found_target = False
    for directive in resolved_directives:
        if "Users" in directive.target:
            assert "SYS_OPERATOR" not in directive.target
            assert current_user in directive.target
            found_target = True
            
    assert found_target is True


