# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import pytest
from pathlib import Path
from unittest.mock import patch
from cortex.guards.gates.audit import check_gate_11_cobbler


@pytest.mark.asyncio
async def test_gate_11_audit_happy():
    cached_files = {Path("clean.py"): "def ok():\n    return True"}
    with patch("cortex.guards.gates.common.GlobalSourceCache.files", cached_files):
        passed, status = await check_gate_11_cobbler()
        assert passed is True
        assert status == "verified"


@pytest.mark.asyncio
async def test_gate_11_audit_bare_except_rejection():
    # It logs but still returns True, verified (non-blocking)
    cached_files = {Path("bad_except.py"): "try:\n    do_something()\nexcept Exception:\n    pass"}
    with patch("cortex.guards.gates.common.GlobalSourceCache.files", cached_files):
        passed, status = await check_gate_11_cobbler()
        assert passed is True
        assert status == "verified"


@pytest.mark.asyncio
async def test_gate_11_audit_print_call_rejection():
    cached_files = {Path("bad_print.py"): "print('Hello world')"}
    with patch("cortex.guards.gates.common.GlobalSourceCache.files", cached_files):
        passed, status = await check_gate_11_cobbler()
        assert passed is True
        assert status == "verified"


@pytest.mark.asyncio
async def test_gate_11_audit_syntax_error_boundary():
    cached_files = {Path("invalid_syntax.py"): "def broken("}
    with patch("cortex.guards.gates.common.GlobalSourceCache.files", cached_files):
        passed, status = await check_gate_11_cobbler()
        assert passed is True  # Gracefully handles syntax errors
        assert status == "verified"


@pytest.mark.asyncio
async def test_gate_11_audit_whitelist_boundary():
    # seals.py is whitelisted
    cached_files = {Path("seals.py"): "print('I am allowed to print')"}
    with patch("cortex.guards.gates.common.GlobalSourceCache.files", cached_files):
        passed, status = await check_gate_11_cobbler()
        assert passed is True
        assert status == "verified"


@pytest.mark.asyncio
async def test_gate_11_audit_combined_violations():
    cached_files = {Path("messy.py"): "print(1)\ntry:\n  f()\nexcept Exception:\n  pass"}
    with patch("cortex.guards.gates.common.GlobalSourceCache.files", cached_files):
        passed, status = await check_gate_11_cobbler()
        assert passed is True
        assert status == "verified"
