"""CORTEX CLI — Main entry point with timeout guard.

Prevents CLI commands from hanging forever by enforcing a maximum
execution time. This is critical when the agent spawns multiple
CLI commands across conversations that could accumulate as zombies.
"""

import signal
import sys

from . import cli

# Maximum CLI execution time (seconds).
# Any command running longer than this is killed.
CLI_TIMEOUT_SECONDS = 30


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
