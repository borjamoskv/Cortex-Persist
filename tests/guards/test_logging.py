# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from babylon60.guards.seals import check_seal_1_code_quality, GlobalSourceCache
from pathlib import Path


@pytest.fixture
def mock_cache():
    GlobalSourceCache.files = {}
    GlobalSourceCache._loaded = True
    yield GlobalSourceCache
    GlobalSourceCache.files = {}
    GlobalSourceCache._loaded = False


@pytest.mark.asyncio
async def test_verify_seal_printer_logging(mock_cache):
    mock_cache.files = {Path("large.py"): "\n" * 800}

    with (
        patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run,
        patch("cortex.guards._seals_checks_1_5.printer") as mock_printer,
    ):
        mock_run.return_value = (0, "Ruff OK")

        await check_seal_1_code_quality()

        # Verify seal initialization was called
        mock_printer.seal.assert_called_with(
            1, "AX-IV Thermodynamic Cognition", "Code Quality (Ruff + LOC ≤700)"
        )

        # Verify success message for Ruff
        mock_printer.success.assert_any_call("Ruff checks passed.")

        # Verify failure message for LOC violation
        mock_printer.fail.assert_any_call("large.py exceeds 700 LOC (801)")


@pytest.mark.asyncio
async def test_verify_seal_printer_ruff_fail(mock_cache):
    mock_cache.files = {Path("ok.py"): "code"}

    with (
        patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run,
        patch("cortex.guards._seals_checks_1_5.printer") as mock_printer,
    ):
        mock_run.return_value = (1, "Ruff Error Output")

        await check_seal_1_code_quality()

        mock_printer.fail.assert_any_call("Ruff linting failed.")
        mock_printer.print.assert_called()
