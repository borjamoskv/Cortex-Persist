"""
CORTEX v5.0 — MEJORAlo Ouroboros Daemon.

Replaces loop_mejoralo.sh with a sovereign, cross-platform Python implementation.
Ensures continuous code quality evolution with graceful handling.
"""

import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def run_mejoralo(project: str, path: Path) -> int:
    """Execute the MEJORAlo scan via CLI."""
    python_exe = sys.executable
    cmd = [python_exe, "-m", "cortex.cli", "mejoralo", "scan", project, str(path)]

    print(f"\n{'='*60}")
    print(f"⚡ [{datetime.now().strftime('%H:%M:%S')}] EXECUTING MEJORAlo")
    print(f"{'='*60}")

    try:
        # Use check=False to mirror the shell behavior of checking exit code manually
        result = subprocess.run(cmd, cwd=str(path), check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error invoking MEJORAlo: {e}")
        return 1


def main():
    project = "cortex"
    path = Path.home() / "cortex"

    # Configuration
    SLEEP_SUCCESS = 1800  # 30 minutes
    SLEEP_ERROR = 30     # 30 seconds

    print("☠️ Starting MEJORAlo Ouroboros Loop (Sovereign Python Mode)...")
    print("Press Ctrl+C to stop the evolution.\n")

    def signal_handler(sig, frame):
        print("\n\n[Sovereign Daemon] Termination signal received. Stopping Ouroboros...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        exit_code = run_mejoralo(project, path)

        if exit_code != 0:
            print(f"\n⚠️ MEJORAlo detected an error or was aborted (Exit: {exit_code}).")
            print(f"⏳ Pausing {SLEEP_ERROR}s before retry...")
            time.sleep(SLEEP_ERROR)
        else:
            print("\n✅ MEJORAlo finished this wave successfully.")
            print(f"⏳ Resting {SLEEP_SUCCESS/60:.0f} minutes before the next evolutionary phase...")
            time.sleep(SLEEP_SUCCESS)


if __name__ == "__main__":
    main()
