import pytest
from decimal import Decimal
from cortex.swarm.omega_daemon import ExergyGuard


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
    from cortex.swarm.omega_daemon import OmegaKernel

    kernel = OmegaKernel(tick_rate_seconds=1)

    # Simular una carga masiva de entropía
    kernel.guard.consume(Decimal("1000.0"))  # Dejar exergía a 0
    assert kernel.guard.current_exergy == Decimal("0.0")

    import asyncio

    async def mock_scan():
        return Decimal("50.0")

    kernel.sensor.scan = mock_scan

    # Ejecutamos un latido
    await kernel._metabolize()

    # Verificamos que la exergía no bajó de 0 y el sistema no crashó
    assert kernel.guard.current_exergy == Decimal("0.0")
