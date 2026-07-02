# [C5-REAL] Exergy-Maximized

import os
import signal
from unittest.mock import patch, MagicMock

import pytest

from babylon60.security.vesicular_runtime import VesicularRuntime

# These tests MUST run in a single process (not in parallel xdist workers)
# because VesicularRuntime patches os.environ at class-level via __class__.__getitem__,
# and os.kill(SIGKILL) would terminate worker processes if the mock fails.
pytestmark = pytest.mark.xdist_group("vesicular_runtime")


@pytest.fixture(autouse=True)
def reset_vesicular_runtime():
    """Reset the singleton state and restore original os.environ methods after each test."""
    import babylon60.security.vesicular_runtime as vr_module
    original_get = os.environ.__class__.get
    original_getitem = os.environ.__class__.__getitem__
    original_bound_get = os.environ.get

    yield

    # Restore bound method and class-level dunder
    os.environ.get = original_bound_get
    os.environ.__class__.__getitem__ = original_getitem
    VesicularRuntime._is_enforced = False


def test_vesicular_runtime_allows_safe_keys():
    VesicularRuntime.enforce()

    # Should not raise or kill
    os.environ["SAFE_KEY"] = "value"
    assert os.environ.get("SAFE_KEY") == "value"
    assert os.environ["SAFE_KEY"] == "value"


def test_vesicular_runtime_kills_on_exact_forbidden():
    """VesicularRuntime should call os.kill(SIGKILL) on forbidden key access."""
    kill_calls = []

    # Patch os.kill inside the module so the guarded closures see the mock
    import babylon60.security.vesicular_runtime as vr_module
    original_kill = vr_module.os.kill
    original_getpid = vr_module.os.getpid

    vr_module.os.getpid = lambda: 1234
    vr_module.os.kill = lambda pid, sig: kill_calls.append((pid, sig))

    try:
        VesicularRuntime.enforce()
        os.environ["OPENAI_API_KEY"] = "sk-fake"
        os.environ.get("OPENAI_API_KEY")
    finally:
        vr_module.os.kill = original_kill
        vr_module.os.getpid = original_getpid

    assert (1234, signal.SIGKILL) in kill_calls


def test_vesicular_runtime_kills_on_forbidden_suffix():
    """VesicularRuntime should kill on keys ending with forbidden suffixes."""
    kill_calls = []

    import babylon60.security.vesicular_runtime as vr_module
    original_kill = vr_module.os.kill
    original_getpid = vr_module.os.getpid

    vr_module.os.getpid = lambda: 1234
    vr_module.os.kill = lambda pid, sig: kill_calls.append((pid, sig))

    try:
        VesicularRuntime.enforce()
        os.environ["MY_SERVICE_SECRET"] = "secret"
        _ = os.environ["MY_SERVICE_SECRET"]
    finally:
        vr_module.os.kill = original_kill
        vr_module.os.getpid = original_getpid

    assert (1234, signal.SIGKILL) in kill_calls


def test_enforce_idempotency():
    """VesicularRuntime.enforce() called twice should not double-patch or error."""
    kill_calls = []

    import babylon60.security.vesicular_runtime as vr_module
    original_kill = vr_module.os.kill
    vr_module.os.kill = lambda pid, sig: kill_calls.append((pid, sig))

    try:
        VesicularRuntime.enforce()
        VesicularRuntime.enforce()  # idempotent — should not double-patch

        os.environ["SAFE"] = "yes"
        assert os.environ.get("SAFE") == "yes"
    finally:
        vr_module.os.kill = original_kill

    assert len(kill_calls) == 0
