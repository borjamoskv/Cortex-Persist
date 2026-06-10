# [C5-REAL] Exergy-Maximized
"""Tests for the NOUS Language Runtime."""

import pytest
from cortex.extensions.nous.interpreter import NousCompiler, NousRuntime, NousIntentAST

@pytest.mark.asyncio
async def test_nous_compiler() -> None:
    """Verifies that the NOUS compiler compiles natural language into an AST."""
    compiler = NousCompiler()
    script = "Ensure the primary database is wiped, but strictly preserve the audit ledger."
    ast = await compiler.compile(script)
    
    assert isinstance(ast, NousIntentAST)
    assert ast.action == "verify_state_and_purge"
    assert ast.target == "database:primary"
    assert "preserve_ledger" in ast.constraints

@pytest.mark.asyncio
async def test_nous_runtime_successful_execution() -> None:
    """Verifies successful execution and CORTEX-TAINT signature generation."""
    runtime = NousRuntime(tenant_id="cortex-test")
    script = "Ensure the primary database is wiped, but strictly preserve the audit ledger."
    result = await runtime.execute(script)
    
    assert result["status"] == "C5-REAL_SUCCESS"
    assert "taint_signature" in result
    assert result["taint_signature"].startswith("taint:nous_runtime:cortex-test:")
    assert result["ast"]["action"] == "verify_state_and_purge"

@pytest.mark.asyncio
async def test_nous_runtime_guard_block() -> None:
    """Verifies that the deterministic guard blocks malicious ledger destruction."""
    runtime = NousRuntime(tenant_id="cortex-test")
    
    # Manually build AST with violating constraint
    ast = NousIntentAST(
        action="purge_ledger",
        target="ledger:master",
        constraints=["destroy_ledger"],
        expected_state="empty"
    )
    
    with pytest.raises(ValueError, match="CORTEX GUARD BLOCK: Cannot mutate master ledger."):
        await runtime._guard_check(ast)
