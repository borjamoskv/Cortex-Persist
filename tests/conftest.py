import re
import subprocess

import pytest

from cortex import api_state, config

# Minimum age (seconds) before a cortex.cli process is considered a zombie.
_ZOMBIE_AGE_THRESHOLD = 10


def _parse_etime(etime: str) -> int:
    """Parse ps etime format (DD-HH:MM:SS, HH:MM:SS, MM:SS, SS) to seconds."""
    etime = etime.strip()
    days = 0
    if "-" in etime:
        d, etime = etime.split("-", 1)
        days = int(d)
    parts = etime.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return days * 86400 + parts[0] * 60 + parts[1]
    return days * 86400 + parts[0]


def _kill_stale_cli_processes() -> None:
    """Kill cortex.cli processes older than threshold, sparing in-flight stores."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,etime,args"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "cortex.cli" not in line or "store" not in line and "export" not in line:
                continue
            match = re.match(r"\s*(\d+)\s+(\S+)\s+(.+)", line)
            if not match:
                continue
            pid, etime, _ = match.groups()
            if _parse_etime(etime) >= _ZOMBIE_AGE_THRESHOLD:
                subprocess.run(["kill", pid], capture_output=True, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass  # Best-effort


@pytest.fixture(scope="session", autouse=True)
def kill_stale_cortex_processes():
    """Kill stale cortex.cli processes (>10s old) before the test session.

    Only targets zombies — preserves in-flight stores from parallel agents.
    """
    _kill_stale_cli_processes()
    yield



@pytest.fixture(autouse=True)
def reset_cortex_state():
    """Reset global state and config between every test."""
    # 1. Reset api_state
    api_state.engine = None
    api_state.auth_manager = None
    api_state.tracker = None

    # 2. Reset config from environment
    config.reload()

    yield

    # 3. Cleanup after test
    api_state.engine = None
    api_state.auth_manager = None
    api_state.tracker = None
    config.reload()


@pytest.fixture(autouse=True)
def bypass_min_content_length():
    from cortex.facts.manager import FactManager

    original = FactManager.MIN_CONTENT_LENGTH
    FactManager.MIN_CONTENT_LENGTH = 1
    yield
    FactManager.MIN_CONTENT_LENGTH = original
