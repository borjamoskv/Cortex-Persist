import pytest
import subprocess
import time

def test_omega_daemon_start_stop():
    """OmegaDaemon inicia y se detiene sin crash."""
    try:
        proc = subprocess.run(
            ["python3", "-u", "cortex/engine/omega_daemon.py"],
            capture_output=True, text=True, timeout=3
        )
        # If it somehow exited quickly, verify stdout
        assert "OmegaDaemon started" in proc.stdout or "C5-REAL" in proc.stdout
    except subprocess.TimeoutExpired as e:
        # Check if daemon initialized correctly before timeout
        stdout_bytes = e.stdout or b""
        stdout = stdout_bytes.decode("utf-8") if isinstance(stdout_bytes, bytes) else stdout_bytes
        assert "OmegaDaemon started" in stdout or "C5-REAL" in stdout

def test_exergy_guard_check():
    """ExergyGuard.check() devuelve dict con RAM + critical."""
    import cortex.engine.omega_daemon as omega
    guard = omega.ExergyGuard(ram_threshold_mb=200.0)
    result = guard.check()
    assert "ram_free_mb" in result
    assert "critical" in result
    assert isinstance(result["ram_free_mb"], (int, float))

def test_entropy_sensor_sense():
    """EntropySensor.sense() devuelve dict con CPU + swap."""
    import cortex.engine.omega_daemon as omega
    sensor = omega.EntropySensor()
    result = sensor.sense()
    assert "cpu_load" in result
    assert "swap_mb" in result
    assert isinstance(result["cpu_load"], (int, float))
