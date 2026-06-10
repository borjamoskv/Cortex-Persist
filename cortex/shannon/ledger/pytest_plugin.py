"""
Pytest plugin for C5-REAL execution mode.
Enforces that tests run under deterministic constraints.
"""

import os

import pytest

from cortex.shannon.ledger.determinism import apply_deterministic_patches


def pytest_addoption(parser):
    """Add custom CLI options to pytest."""
    parser.addoption(
        "--c5-real",
        action="store_true",
        default=False,
        help="Enable C5-REAL mode: strict deterministic testing",
    )


def pytest_configure(config):
    """Configure pytest based on CLI options."""
    if config.getoption("--c5-real"):
        # Set environment variable so the rest of the application knows
        os.environ["CORTEX_C5_REAL_MODE"] = "1"
        # Apply determinism patches early
        apply_deterministic_patches()


@pytest.fixture(autouse=True)
def c5_real_env(request):
    """Fixture that automatically applies deterministic patches if --c5-real is used."""
    if request.config.getoption("--c5-real"):
        apply_deterministic_patches()

        # You could also add other strict checks here, e.g. failing tests if they
        # try to perform unexpected non-deterministic behavior.
