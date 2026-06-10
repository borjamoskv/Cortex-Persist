import pytest
from cortex.shannon.ledger.determinism import inject_determinism

def pytest_configure(config):
    """
    Called after command line options have been parsed and all plugins and
    initial conftest files been loaded.
    Inject deterministic seeds for C5-REAL tests.
    """
    inject_determinism()

def pytest_runtest_setup(item):
    """
    Called before pytest_runtest_call().
    Re-inject determinism before each test to ensure no state leakage
    breaks the C5-REAL determinism constraint.
    """
    inject_determinism()
