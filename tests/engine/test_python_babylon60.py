# [C5-REAL] Exergy-Maximized Test Suite
import pytest
from babylon60.engine.babylon60 import Babylon60
from babylon60.engine.exergy_optimizer import ExergyOptimizer
from babylon60.engine.swarm_10k import NodeMetrics


def test_python_babylon60_init():
    a = Babylon60(1)
    assert a._value == 3600

    b = Babylon60(0.5)
    assert b._value == 1800

    c = Babylon60(a)
    assert c._value == 3600

    with pytest.raises(TypeError):
        Babylon60("anergy")


def test_python_babylon60_arithmetic():
    a = Babylon60(1.0)
    b = Babylon60(0.5)

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
    assert 1.5 + b == Babylon60(2.0)
    assert 1.0 - b == Babylon60(0.5)
    assert 2.0 * b == Babylon60(1.0)
    assert 1.0 / b == Babylon60(2.0)


def test_python_babylon60_errors():
    a = Babylon60(1.0)
    with pytest.raises(ZeroDivisionError):
        _ = a / Babylon60(0.0)

    # Coercion succeeds for int
    assert a + 5 == Babylon60(6.0)

    # Invalid type raises TypeError
    with pytest.raises(TypeError):
        _ = a + "invalid"


def test_python_babylon60_comparisons():
    a = Babylon60(1.0)
    b = Babylon60(2.0)
    c = Babylon60(1.0)

    assert a < b
    assert a <= b
    assert b > a
    assert b >= a
    assert a == c
    assert a != b


def test_exergy_optimizer_babylon60():
    metrics = NodeMetrics(
        exergy=Babylon60(1.0),
        uncertainty=Babylon60(0.0),
        active_children=0
    )

    # Optimum condition: active=0, latency=0
    exergy = ExergyOptimizer.calculate_node_exergy(
        metrics, latency_ms=Babylon60(0.0), max_capacity=100
    )
    assert exergy == Babylon60(1.0)

    # Degraded condition: latency=20ms (exceeds threshold 16ms), active=50
    metrics_degraded = NodeMetrics(
        exergy=Babylon60(1.0),
        uncertainty=Babylon60(0.1),
        active_children=50
    )
    exergy_degraded = ExergyOptimizer.calculate_node_exergy(
        metrics_degraded, latency_ms=Babylon60(20.0), max_capacity=100
    )
    # density_factor = 1 - 50/100 = 0.5
    # latency_factor = 1 - (20 - 16)/32 = 1 - 4/32 = 0.875
    # uncertainty_penalty = 1 - 0.1 = 0.9
    # expected exergy = 0.5 * 0.875 * 0.9 = 0.39375 -> Babylon60(0.39375)
    # raw value: 3600 * 0.5 = 1800
    # 1800 * 0.875 = 1575
    # 1575 * 0.9 = 1417.5 -> 1417 raw value
    assert exergy_degraded._value == 1417
