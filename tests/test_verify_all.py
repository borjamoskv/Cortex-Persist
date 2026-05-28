import sqlite3
from pathlib import Path

from click.testing import CliRunner

from cortex.cli.main import cli
from cortex.consensus.merkle import MerkleTree
from cortex.ledger.ledger_core import SovereignLedger
from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier
from cortex.ledger.writer import LedgerWriter


def _seed_dual_ledgers(db_path: Path) -> LedgerStore:
    store = LedgerStore(db_path)
    writer = LedgerWriter(store, EnrichmentQueue(store))
    verifier = LedgerVerifier(store)

    event = LedgerEvent.new(
        tool="cli",
        actor="test-actor",
        action="store",
        target=ActionTarget(app="Test"),
        result=ActionResult(ok=True, latency_ms=1),
        metadata={"project": "verify-all"},
    )
    writer.append(event)
    assert verifier.create_checkpoint(batch_size=1) is not None

    with sqlite3.connect(db_path) as conn:
        ledger = SovereignLedger(conn)
        ledger.record_transaction("verify-all", "store", {"ok": True}, tenant_id="tenant-a")
        tx_id, tx_hash = conn.execute("SELECT id, hash FROM transactions").fetchone()
        conn.execute(
            "INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count) "
            "VALUES (?, ?, ?, ?)",
            (MerkleTree([tx_hash]).root, tx_id, tx_id, 1),
        )
        conn.commit()

    return store


def test_verify_all_covers_both_ledgers(tmp_path: Path) -> None:
    store = _seed_dual_ledgers(tmp_path / "verify_all.db")

    result = LedgerVerifier(store).verify_all()

    assert result["valid"] is True
    assert result["sections"]["ledger_events"]["checked_events"] == 1
    assert result["sections"]["ledger_checkpoints"]["checked_checkpoints"] == 1
    assert result["sections"]["transactions"]["checked_transactions"] == 1
    assert result["sections"]["merkle_roots"]["checked_checkpoints"] == 1


def test_verify_all_reports_transaction_and_event_tamper(tmp_path: Path) -> None:
    store = _seed_dual_ledgers(tmp_path / "verify_all_tamper.db")

    with store.tx() as conn:
        conn.execute("UPDATE ledger_events SET hash = 'BAD_EVENT_HASH'")
        conn.execute("UPDATE transactions SET hash = 'BAD_TX_HASH'")

    result = LedgerVerifier(store).verify_all()

    assert result["valid"] is False
    assert "ledger_events" in result["violations"]
    assert "transactions" in result["violations"]


def test_verify_all_reports_checkpoint_mismatch(tmp_path: Path) -> None:
    store = _seed_dual_ledgers(tmp_path / "verify_all_checkpoint.db")

    with store.tx() as conn:
        conn.execute("UPDATE ledger_checkpoints SET root_hash = 'BAD_EVENT_ROOT'")
        conn.execute("UPDATE merkle_roots SET root_hash = 'BAD_TX_ROOT'")

    result = LedgerVerifier(store).verify_all()

    assert result["valid"] is False
    assert "ledger_checkpoints" in result["violations"]
    assert "merkle_roots" in result["violations"]


def test_cortex_verify_all_cli(tmp_path: Path) -> None:
    _seed_dual_ledgers(tmp_path / "verify_all_cli.db")

    result = CliRunner().invoke(
        cli,
        ["verify", "all", "--db", str(tmp_path / "verify_all_cli.db")],
    )

    assert result.exit_code == 0, result.output
    assert "All ledger surfaces are VALID" in result.output


def test_trust_ledger_verify_all_cli(tmp_path: Path) -> None:
    _seed_dual_ledgers(tmp_path / "trust_ledger_verify_all_cli.db")

    result = CliRunner().invoke(
        cli,
        ["trust-ledger", "verify", "--all", "--db", str(tmp_path / "trust_ledger_verify_all_cli.db")],
    )

    assert result.exit_code == 0, result.output
    assert "All ledger surfaces are VALID" in result.output
