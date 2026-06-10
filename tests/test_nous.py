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
        expected_state="empty",
    )

    with pytest.raises(ValueError, match="CORTEX GUARD BLOCK: Cannot mutate master ledger."):
        await runtime._guard_check(ast)


def test_ast_nous_compiler() -> None:
    """Verifies the file-based NOUS AST Compiler."""
    from cortex.extensions.nous.compiler import NousCompiler as ASTNousCompiler

    compiler = ASTNousCompiler()
    raw_nous = """
    intent TestIntent {
      ensure database is optimized
      preserve audit_ledger
      require disk_space > 10
    }
    """
    intent = compiler.parse(raw_nous)
    assert intent.name == "TestIntent"
    assert "database is optimized" in intent.ensures
    assert "audit_ledger" in intent.preserves
    assert "disk_space > 10" in intent.requires

    ast_nodes = compiler.compile(intent)
    assert len(ast_nodes) == 1
    assert ast_nodes[0].action_type == "migrate_schema"
    assert ast_nodes[0].target == "database is optimized"
