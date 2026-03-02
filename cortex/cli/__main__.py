"""CORTEX CLI — Main entry point with timeout guard.

Prevents CLI commands from hanging forever by enforcing a maximum
execution time. This is critical when the agent spawns multiple
CLI commands across conversations that could accumulate as zombies.
"""

import signal
import sys

from . import cli

# Maximum CLI execution time (seconds).
# Must be > (BUSY_TIMEOUT_MS/1000 + model_load_time) to avoid SIGALRM
# killing the process before SQLite can retry a write lock.
# BUSY_TIMEOUT_MS = 30s + ~10s model load = 40s minimum → 60s safe ceiling.
CLI_TIMEOUT_SECONDS = 60


def _timeout_handler(signum: int, frame: object) -> None:
    """Force-kill the process when timeout expires."""
    print(
        f"\n⏱️ CORTEX CLI: timeout after {CLI_TIMEOUT_SECONDS}s — self-terminating",
        file=sys.stderr,
    )
    sys.exit(124)  # Standard timeout exit code


if __name__ == "__main__":
    # Install timeout guard (SIGALRM, Unix-only)
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(CLI_TIMEOUT_SECONDS)

    cli()
