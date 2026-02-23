import subprocess

import pytest

from cortex import api_state, config


@pytest.fixture(scope="session", autouse=True)
def kill_stale_cortex_processes():
    """Kill stale cortex.cli processes before the test session starts.

    Prevents zombie accumulation from prior conversations/runs that
    would hold SQLite locks and cause cascade hangs.
    """
    subprocess.run(
        ["pkill", "-f", "cortex.cli store"],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["pkill", "-f", "cortex.cli export"],
        capture_output=True,
        check=False,
    )
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
