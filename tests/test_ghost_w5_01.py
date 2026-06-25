# [C5-REAL] Exergy-Maximized

import os
import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from legacy_research.cli import cli
from legacy_research.ledger.models import ActionResult, ActionTarget, LedgerEvent
from legacy_research.ledger.queue import EnrichmentQueue
from legacy_research.ledger.store import LedgerStore
from legacy_research.ledger.verifier import LedgerVerifier
from legacy_research.ledger.writer import LedgerWriter
from legacy_research.ledger.public_verifier import verify_export


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "cortex_test_ghost_w5.db"
    return db_path


def test_e2e_ledger_integrity_and_export(temp_db: Path, tmp_path: Path) -> None:
    # 1. Initialize store and writer
    db_str = str(temp_db)
    store = LedgerStore(db_str)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)

    # 2. Append events to database
    t = ActionTarget(app="GhostTestApp")
    r = ActionResult(ok=True, latency_ms=15)

    for i in range(5):
        ev = LedgerEvent.new(
            tool="ghost-verifier",
            actor="ghost-actor",
            action=f"ghost.action.{i}",
            target=t,
            result=r,
            metadata={"project": "ghost-w5"},
        )
        writer.append(ev)

    # 3. Create a Merkle checkpoint
    root_id = verifier.create_checkpoint(batch_size=5)
    assert root_id is not None

    # 4. Invoke CLI 'verify' command and assert output structure contains Merkle Tree representation
    runner = CliRunner()
    verify_result = runner.invoke(cli, ["trust-ledger", "verify", "--db", db_str])
    assert verify_result.exit_code == 0
    assert "Ledger is VALID" in verify_result.output
    assert "Merkle Checkpoints" in verify_result.output
    assert f"Checkpoint #{root_id}" in verify_result.output
    assert "Node L1:" in verify_result.output
    assert "Leaf 0" in verify_result.output

    # 5. Invoke CLI 'export' command to forensic public-v1-strict format
    export_dir = tmp_path / "ghost-export"
    export_result = runner.invoke(
        cli,
        [
            "trust-ledger",
            "export",
            str(export_dir),
            "--db",
            db_str,
            "--tenant-id",
            "ghost-tenant",
            "--stream-id",
            "tenant:ghost-tenant:ledger:primary",
            "--include-verification-report",
        ],
    )
    assert export_result.exit_code == 0

    # Ensure JSON response matches expected schema
    output_json = json.loads(export_result.output)
    assert "export_dir" in output_json
    assert "manifest_hash" in output_json
    assert output_json["verification_result"] == "VALID_FULL_STRICT"

    # 6. Verify forensic package with public_verifier
    report = verify_export(export_dir)
    assert report["result"] == "VALID_FULL_STRICT"
    assert report["guarantees"]["integrity_verified"] is True
    assert report["guarantees"]["origin_authenticity_verified"] is True
    assert report["guarantees"]["authority_verified"] is True
    assert report["guarantees"]["completeness_verified"] is True
