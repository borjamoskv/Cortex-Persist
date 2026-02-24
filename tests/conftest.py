import base64
import os
import re
import subprocess

import pytest

import cortex.api.state as api_state
from cortex import config

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
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
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


@pytest.fixture(scope="session", autouse=True)
def set_test_master_key():
    import base64
    import os

    # 32 bytes key base64 encoded
    key = base64.b64encode(b"test_key_that_must_be_32_bytes_x").decode("utf-8")
    os.environ["CORTEX_VAULT_KEY"] = key
    os.environ["CORTEX_TESTING"] = "1"
    yield
    os.environ.pop("CORTEX_VAULT_KEY", None)
    os.environ.pop("CORTEX_TESTING", None)


@pytest.fixture(autouse=True)
def bypass_min_content_length():
    from cortex.facts.manager import FactManager
    from cortex.engine.store_mixin import StoreMixin

    orig_fm = FactManager.MIN_CONTENT_LENGTH
    orig_sm = StoreMixin.MIN_CONTENT_LENGTH
    FactManager.MIN_CONTENT_LENGTH = 1
    StoreMixin.MIN_CONTENT_LENGTH = 1
    yield
    FactManager.MIN_CONTENT_LENGTH = orig_fm
    StoreMixin.MIN_CONTENT_LENGTH = orig_sm


@pytest.fixture(scope="session", autouse=True)
def setup_test_master_key():
    """Ensure a Master Key is available for L3 Ledger encryption during tests."""
    from cortex.crypto.aes import reset_default_encrypter

    # 32 bytes of zeros in base64
    test_key = base64.b64encode(b"\x00" * 32).decode("utf-8")
    os.environ["CORTEX_MASTER_KEY"] = test_key

    # Reset singleton to ensure it picks up the new env var
    reset_default_encrypter()

    yield

    # We don't necessarily need to unset it, but reset the singleton
    reset_default_encrypter()
