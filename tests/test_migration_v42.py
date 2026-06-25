import pytest
from datetime import datetime, timezone
import hashlib

from legacy_research.engine import CortexEngine
from legacy_research.extensions.nous.runtime import NousRuntime
from legacy_research.extensions.nous.models import (
    NousAST,
    NousMetadata,
    NousOperation,
    NousInvariant,
    MigrationTaint,
)


@pytest.mark.asyncio
async def test_migration_v42_dry_run_and_taint(tmp_path):
    # Setup Engine and Runtime
    db_path = str(tmp_path / "test_migration.db")
    engine = CortexEngine(db_path=db_path)
    runtime = NousRuntime(engine)

    # 1. Define Migration AST
    ast = NousAST(
        metadata=NousMetadata(
            version="v42",
            author="borjamoskv",
            description="C5-REAL Taint Verification Migration",
        ),
        ensures=["table_schema_verified"],
        operations=[
            NousOperation(
                type="create_table",
                target="nexus_ledger",
                sql="CREATE TABLE nexus_ledger (id UUID PRIMARY KEY, taint_hash TEXT);",
                rollback_sql="DROP TABLE nexus_ledger;",
            )
        ],
        invariants=[NousInvariant(name="no_data_loss", condition="true", action="halt")],
    )

    # 2. Execute Dry Run
    dry_run_result = await runtime.dry_run(ast)

    # Verify Dry Run
    assert dry_run_result.ok is True, "Dry run should pass"
    assert "syntax_check" in dry_run_result.guards
    assert dry_run_result.guards["rollback_check"].passed is True
    assert dry_run_result.estimated_data_loss_risk == "none"

    # 3. Execute Real Migration and verify Ledger
    await runtime.execute(ast, dry_run_result)

    # 4. Assert Ledger Integrity
    assert len(runtime.ledger.chain) == 2, "Genesis block + 1 mutation"

    mutation_entry = runtime.ledger.chain[-1]
    assert "Migration v42 by borjamoskv. Taint:" in mutation_entry.intent_description
    assert mutation_entry.applied_ast[0]["type"] == "create_table"
    assert mutation_entry.applied_ast[0]["target"] == "nexus_ledger"

    # Ledger cryptographic verification
    assert runtime.ledger.verify_chain() is True, "Ledger cryptographic chain broken"
