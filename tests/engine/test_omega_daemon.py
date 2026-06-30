import pytest
from decimal import Decimal
from babylon60.swarm.omega_daemon import ExergyGuard


def test_exergy_guard_success():
    guard = ExergyGuard(Decimal("10.0"), Decimal("100.0"))
    assert guard.evaluate(Decimal("50.0")) is True
    guard.consume(Decimal("50.0"))
    assert guard.current_exergy == Decimal("50.0")


def test_exergy_guard_failure():
    guard = ExergyGuard(Decimal("10.0"), Decimal("40.0"))
    assert guard.evaluate(Decimal("50.0")) is False


def test_exergy_guard_floor():
    guard = ExergyGuard(Decimal("10.0"), Decimal("40.0"))
    guard.consume(Decimal("50.0"))
    assert guard.current_exergy == Decimal("0.0")


@pytest.mark.asyncio
async def test_omega_kernel_hibernation():
    from babylon60.swarm.omega_daemon import OmegaKernel

    kernel = OmegaKernel(tick_rate_seconds=1)

    # Simulate a massive load of entropy
    kernel.guard.consume(Decimal("1000.0"))  # Dejar exergía a 0
    assert kernel.guard.current_exergy == Decimal("0.0")

    import asyncio

    async def mock_scan():
        return Decimal("50.0")

    kernel.sensor.scan = mock_scan

    # We execute a heartbeat
    await kernel._metabolize()

    # We verify that exergy did not fall below 0 and the system did not crash
    assert kernel.guard.current_exergy == Decimal("0.0")
