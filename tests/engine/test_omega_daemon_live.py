# [C5-REAL] Exergy-Maximized
import subprocess
import time
import signal
import sys
import shutil
import pytest

def test_omega_daemon_cli_lifecycle():
    """Verify that omega daemon CLI starts and can be stopped gracefully."""
    cortex_bin = shutil.which("cortex")
    if not cortex_bin:
        cmd = [sys.executable, "-m", "cortex.cli.main", "omega", "start", "--tick-rate", "1"]
    else:
        cmd = [cortex_bin, "omega", "start", "--tick-rate", "1"]

    # Start the daemon
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Allow it to run for a short duration
    time.sleep(3)

    # Terminate the daemon gracefully via SIGINT (KeyboardInterrupt)
    proc.send_signal(signal.SIGINT)

    try:
        stdout, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        pytest.fail(f"Omega daemon did not terminate in time. Stderr: {stderr}")

    # KeyboardInterrupt caught inside main will exit cleanly (0 or -SIGINT)
    assert proc.returncode in (0, -signal.SIGINT), f"Unexpected exit code: {proc.returncode}. Stderr: {stderr}"
