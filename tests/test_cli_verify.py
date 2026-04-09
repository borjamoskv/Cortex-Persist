from __future__ import annotations

import sqlite3
from pathlib import Path

from click.testing import CliRunner

from cortex.cli import cli
from cortex.engine import CortexEngine


def _build_demo_db(db_path: Path, *, tamper: bool) -> int:
    """Create a minimal database for CLI integrity verification tests."""
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)
    try:
        engine.init_db_sync()
        engine.store_sync(
            "demo",
            "original content",
            fact_type="knowledge",
            source="manual",
        )
    finally:
        engine.close_sync()

    with sqlite3.connect(db_path) as conn:
        fact_id = int(conn.execute("SELECT id FROM facts ORDER BY id DESC LIMIT 1").fetchone()[0])
        if tamper:
            conn.execute("UPDATE facts SET content = ? WHERE id = ?", ("tampered content", fact_id))
            conn.commit()

    return fact_id


def test_verify_cli_detects_tampered_fact(tmp_path: Path) -> None:
    db_path = tmp_path / "verify-tampered.db"
    fact_id = _build_demo_db(db_path, tamper=True)

    result = CliRunner().invoke(cli, ["verify", str(fact_id), "--db", str(db_path)])

    assert result.exit_code == 0
    assert "Content Integrity" in result.output
    assert "HASH_MISMATCH" in result.output
    assert "INTEGRITY VIOLATION" in result.output


def test_verify_cli_confirms_clean_encrypted_fact(tmp_path: Path) -> None:
    db_path = tmp_path / "verify-clean.db"
    fact_id = _build_demo_db(db_path, tamper=False)

    result = CliRunner().invoke(cli, ["verify", str(fact_id), "--db", str(db_path)])

    assert result.exit_code == 0
    assert "Content Integrity" in result.output
    assert "HASH_MISMATCH" not in result.output
    assert "VERIFIED" in result.output


def test_trust_ledger_full_verify_reports_fact_tampering(tmp_path: Path) -> None:
    db_path = tmp_path / "ledger-full-tampered.db"
    fact_id = _build_demo_db(db_path, tamper=True)

    result = CliRunner().invoke(cli, ["trust-ledger", "verify", "--full", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "Ledger is COMPROMISED" in result.output
    assert "Fact Integrity" in result.output
    assert f"Fact #{fact_id}" in result.output
    assert "HASH_MISMATCH" in result.output


def test_trust_ledger_full_verify_confirms_clean_facts(tmp_path: Path) -> None:
    db_path = tmp_path / "ledger-full-clean.db"
    _build_demo_db(db_path, tamper=False)

    result = CliRunner().invoke(cli, ["trust-ledger", "verify", "--full", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "Ledger is VALID" in result.output
    assert "Fact Integrity: OK" in result.output
