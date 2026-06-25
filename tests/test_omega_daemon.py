import pytest
import asyncio
import legacy_research.engine.omega_daemon as omega

@pytest.mark.asyncio
async def test_omega_daemon_start_stop():
    """OmegaDaemon inicia y se detiene sin crash usando asyncio."""
    daemon = omega.OmegaDaemon(reclaim_on_critical=False)
    task = asyncio.create_task(daemon.start(interval_s=0.05))
    await asyncio.sleep(0.1)
    daemon.stop()
    await task
    assert daemon.loop_count >= 1

def test_exergy_guard_check():
    """ExergyGuard.check() devuelve dict con RAM + critical."""
    guard = omega.ExergyGuard(ram_threshold_mb=200.0)
    result = guard.check()
    assert "ram_free_mb" in result
    assert "critical" in result
    assert isinstance(result["ram_free_mb"], (int, float))

def test_entropy_sensor_sense():
    """EntropySensor.sense() devuelve dict con CPU + swap."""
    sensor = omega.EntropySensor()
    result = sensor.sense()
    assert "cpu_load" in result
    assert "swap_mb" in result
    assert isinstance(result["cpu_load"], (int, float))
