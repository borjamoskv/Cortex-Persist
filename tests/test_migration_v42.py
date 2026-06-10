import pytest
from datetime import datetime, timezone
import hashlib

from cortex.engine import CortexEngine
from cortex.extensions.nous.runtime import NousRuntime
from cortex.extensions.nous.models import (
    NousAST,
    NousMetadata,
    NousOperation,
    NousInvariant,
    MigrationTaint
)

@pytest.mark.asyncio
async def test_migration_v42_dry_run_and_taint():
    # Setup Engine and Runtime
    engine = CortexEngine()
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
                rollback_sql="DROP TABLE nexus_ledger;"
            )
        ],
        invariants=[
            NousInvariant(
                name="no_data_loss",
                condition="true",
                action="halt"
            )
        ]
    )

    # 2. Execute Dry Run
    dry_run_result = await runtime.dry_run(ast)
    
    # Verify Dry Run
    assert dry_run_result.ok is True, "Dry run should pass"
    assert "syntax_check" in dry_run_result.guards
    assert dry_run_result.guards["rollback_check"].passed is True
    assert dry_run_result.estimated_data_loss_risk == "none"

    # 3. Verify Taint Generation (Simulated as it would be in a CI pipeline)
    # The taint locks the migration state in C5-REAL
    manifest_str = ast.model_dump_json()
    manifest_hash = hashlib.sha256(manifest_str.encode()).hexdigest()
    
    dry_run_str = dry_run_result.model_dump_json()
    dry_run_hash = hashlib.sha256(dry_run_str.encode()).hexdigest()
    
    predicted_state_hash = hashlib.sha256(
        str(dry_run_result.predicted_state).encode()
    ).hexdigest()

    taint = MigrationTaint(
        version=ast.metadata.version,
        actor=ast.metadata.author,
        manifest_hash=manifest_hash,
        ast_hash=manifest_hash, # Using manifest hash for AST as well
        dry_run_hash=dry_run_hash,
        predicted_state_hash=predicted_state_hash,
        timestamp=datetime.now(timezone.utc),
        signature="ed25519-simulated-signature-c5-real"
    )

    # Assert taint integrity
    assert taint.version == "v42"
    assert taint.actor == "borjamoskv"
    assert len(taint.manifest_hash) == 64
    assert len(taint.dry_run_hash) == 64
    assert taint.signature.startswith("ed25519")
