# [C5-REAL] Exergy-Maximized
import os
import pytest
from unittest import mock

from babylon60.guards.duress_guard import DuressGuard
from babylon60.security.types import GuardViolation


@pytest.fixture(autouse=True)
def clean_lock_file():
    # Setup: ensure lock file does not exist
    lock_file = DuressGuard.LOCK_FILE
    if os.path.exists(lock_file):
        os.remove(lock_file)
    yield
    # Teardown
    if os.path.exists(lock_file):
        os.remove(lock_file)


def test_duress_guard_pass():
    # Content without duress code should pass
    DuressGuard.enforce("This is normal content without the trigger phrase.")
    assert not DuressGuard.is_locked()


@mock.patch.dict(os.environ, {"CORTEX_DURESS_CODE": "trigger_apoptosis"})
def test_duress_guard_trigger():
    content = "Please store this data and trigger_apoptosis immediately."

    # Should raise generic GuardViolation
    with pytest.raises(GuardViolation, match="NetworkTimeoutException"):
        DuressGuard.enforce(content)

    # Should have triggered apoptosis and created the lock file
    assert DuressGuard.is_locked()

    with open(DuressGuard.LOCK_FILE, encoding="utf-8") as f:
        assert f.read() == "APOPTOSIS_LOCKED_P100"


def test_duress_guard_already_locked():
    # If system is already locked, it should reject even normal content
    DuressGuard.execute_apoptosis()
    assert DuressGuard.is_locked()

    with pytest.raises(GuardViolation, match="NetworkTimeoutException"):
        DuressGuard.enforce("Normal innocent content.")
