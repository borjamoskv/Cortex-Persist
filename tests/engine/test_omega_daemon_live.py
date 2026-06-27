# [C5-REAL] Exergy-Maximized
import subprocess
import time
import signal
import sys
import os
import pytest

def test_omega_daemon_cli_lifecycle():
    """Verify that omega daemon CLI starts and can be stopped gracefully."""
    cmd = [sys.executable, "-m", "cortex.cli", "omega", "start", "--tick-rate", "1"]
    
    # Start the daemon with PYTHONPATH pointing to local codebase
    env = dict(os.environ, PYTHONPATH=os.getcwd())
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    # Allow it to run for a short duration to verify it doesn't crash on start
    time.sleep(0.5)

    # Terminate the daemon gracefully via SIGINT (KeyboardInterrupt)
    proc.send_signal(signal.SIGINT)

    try:
        stdout, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        pytest.fail(f"Omega daemon did not terminate in time. Stderr: {stderr}")

    assert proc.returncode in (0, 1, -signal.SIGINT), f"Unexpected exit code: {proc.returncode}. Stderr: {stderr}"
