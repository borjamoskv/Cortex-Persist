# [C5-REAL] Exergy-Maximized Test Suite
import pytest
from legacy_research.engine.cortex import Cortex
from legacy_research.engine.exergy_optimizer import ExergyOptimizer
from legacy_research.engine.swarm_10k import NodeMetrics


def test_python_cortex_init():
    a = Cortex(1)
    assert a._value == 3600

    b = Cortex(0.5)
    assert b._value == 1800

    c = Cortex(a)
    assert c._value == 3600

    with pytest.raises(TypeError):
        Cortex("anergy")


def test_python_cortex_arithmetic():
    a = Cortex(1.0)
    b = Cortex(0.5)

    c = a + b
    assert c._value == 5400
    assert c.to_float() == 1.5

    d = a - b
    assert d._value == 1800
    assert d.to_float() == 0.5

    e = a * b
    assert e._value == 1800
    assert e.to_float() == 0.5

    f = a / b
    assert f._value == 7200
    assert f.to_float() == 2.0

    # Reflected arithmetic
    assert 1.5 + b == Cortex(2.0)
    assert 1.0 - b == Cortex(0.5)
    assert 2.0 * b == Cortex(1.0)
    assert 1.0 / b == Cortex(2.0)


def test_python_cortex_errors():
    a = Cortex(1.0)
    with pytest.raises(ZeroDivisionError):
        _ = a / Cortex(0.0)

    # Coercion succeeds for int
    assert a + 5 == Cortex(6.0)

    # Invalid type raises TypeError
    with pytest.raises(TypeError):
        _ = a + "invalid"


def test_python_cortex_comparisons():
    a = Cortex(1.0)
    b = Cortex(2.0)
    c = Cortex(1.0)

    assert a < b
    assert a <= b
    assert b > a
    assert b >= a
    assert a == c
    assert a != b


def test_exergy_optimizer_cortex():
    metrics = NodeMetrics(
        exergy=Cortex(1.0),
        uncertainty=Cortex(0.0),
        active_children=0
    )

    # Optimum condition: active=0, latency=0
    exergy = ExergyOptimizer.calculate_node_exergy(
        metrics, latency_ms=Cortex(0.0), max_capacity=100
    )
    assert exergy == Cortex(1.0)

    # Degraded condition: latency=20ms (exceeds threshold 16ms), active=50
    metrics_degraded = NodeMetrics(
        exergy=Cortex(1.0),
        uncertainty=Cortex(0.1),
        active_children=50
    )
    exergy_degraded = ExergyOptimizer.calculate_node_exergy(
        metrics_degraded, latency_ms=Cortex(20.0), max_capacity=100
    )
    # density_factor = 1 - 50/100 = 0.5
    # latency_factor = 1 - (20 - 16)/32 = 1 - 4/32 = 0.875
    # uncertainty_penalty = 1 - 0.1 = 0.9
    # expected exergy = 0.5 * 0.875 * 0.9 = 0.39375 -> Cortex(0.39375)
    # raw value: 3600 * 0.5 = 1800
    # 1800 * 0.875 = 1575
    # 1575 * 0.9 = 1417.5 -> 1417 raw value
    assert exergy_degraded._value == 1417
