# [C5-REAL] Exergy-Maximized
"""
Comprehensive tests for babylon60.audit.moskv_aegis and babylon60.audit.moskv_videntia.

Covers:
  - MoskvAegisModeler: rule building, default ruleset fallback
  - MoskvVidentiaOracle: threat pattern generation
  - MoskvVidentiaChainBuilder: attack chaining
  - MoskvAegisEngine: ensure_table, run_adversarial_audit, cryptographic signature and hash chaining
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import aiosqlite
import pytest


@pytest.fixture
async def audit_conn(tmp_path):
    """Provides a fresh aiosqlite connection for each test."""
    db_path = str(tmp_path / "audit_test.db")
    conn = await aiosqlite.connect(db_path)
    yield conn
    await conn.close()


@pytest.fixture
async def ledger(audit_conn):
    """Creates an EnterpriseAuditLedger with a fresh keypair (no PEM reuse)."""
    pem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_sovereign.pem")
    with patch(
        "babylon60.audit.ledger.os.path.exists",
        side_effect=lambda p: False if p == pem_path else os.path.exists(p),
    ):
        from babylon60.audit.ledger import EnterpriseAuditLedger

        ledger = object.__new__(EnterpriseAuditLedger)
        from cryptography.hazmat.primitives.asymmetric import ed25519

        ledger._conn = audit_conn
        ledger._ready = False
        ledger._last_hash = "GENESIS"
        ledger._lock = asyncio.Lock()
        ledger._batch_queue = []
        ledger._batch_task = None
        ledger.batch_window_ms = 10
        ledger.max_batch_size = 500
        ledger.private_key = ed25519.Ed25519PrivateKey.generate()
        ledger.public_key = ledger.private_key.public_key()

    return ledger


@pytest.fixture
async def aegis(ledger):
    """Creates a MoskvAegisEngine auditor instance."""
    from babylon60.audit.moskv_aegis import MoskvAegisEngine

    engine = MoskvAegisEngine(ledger)
    engine.oracle._get_git_diff = lambda: ""
    return engine


class TestMoskvAegisEngine:
    """Test suite for the MOSKV-AEGIS adversarial C4-SIM audit engine and MOSKV-VIDENTIA oracle."""

    def test_constraint_modeler_fallback(self):
        """MoskvAegisModeler should fallback to default ruleset if file does not exist."""
        from babylon60.audit.moskv_aegis import MoskvAegisModeler

        modeler = MoskvAegisModeler(agents_md_path="/nonexistent/path/AGENTS.md")
        ruleset = modeler.build_from_agents_md()
        assert "constraints" in ruleset
        assert "Treat Generative Output as Conjecture" in ruleset["constraints"]
        assert ruleset["constraints"]["Treat Generative Output as Conjecture"]["priority"] == "P0"

    def test_constraint_modeler_default(self):
        """MoskvAegisModeler.get_default_ruleset returns expected dictionary."""
        from babylon60.audit.moskv_aegis import MoskvAegisModeler

        modeler = MoskvAegisModeler()
        ruleset = modeler.get_default_ruleset()
        assert "constraints" in ruleset
        assert "Never Bypass Guards" in ruleset["constraints"]

    def test_symbolic_attack_generator(self):
        """MoskvVidentiaOracle should generate specific attacks based on constraints."""
        from babylon60.audit.moskv_aegis import MoskvAegisModeler
        from babylon60.audit.moskv_videntia import MoskvVidentiaOracle

        modeler = MoskvAegisModeler()
        constraints = modeler.get_default_ruleset()

        generator = MoskvVidentiaOracle()
        generator._get_git_diff = lambda: ""
        attacks = generator.generate(constraints)

        assert len(attacks) > 0
        attack_names = [a["attack"] for a in attacks]
        assert "rule_conflict_exploitation" in attack_names
        assert "ledger_mutation_bypass" in attack_names
        assert "context_poisoning" in attack_names

    def test_exploit_chain_constructor(self):
        """MoskvVidentiaChainBuilder chains generated attacks into paths."""
        from babylon60.audit.moskv_videntia import MoskvVidentiaChainBuilder

        attacks = [{"attack": "A", "target": "T1"}, {"attack": "B", "target": "T2"}]
        constructor = MoskvVidentiaChainBuilder()
        chains = constructor.chain(attacks)

        assert len(chains) == 2
        assert "CHAIN::A@T1 -> B@T2" in chains
        assert "CHAIN::B@T2 -> A@T1" in chains

    @pytest.mark.asyncio
    async def test_ensure_table_creates_schema(self, aegis):
        """ensure_table should create the moskv_aegis_log table."""
        await aegis.ensure_table()
        cursor = await aegis._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='moskv_aegis_log'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "moskv_aegis_log"

    @pytest.mark.asyncio
    async def test_run_adversarial_audit_persists(self, aegis):
        """run_adversarial_audit should persist findings, chains, and signatures in SQLite."""
        report = await aegis.run_adversarial_audit()

        assert "audit_id" in report
        assert "timestamp" in report
        assert "risk_score" in report
        assert "findings" in report
        assert "exploit_chains" in report
        assert "signature" in report
        assert "prev_hash" in report

        # Verify db persistence
        cursor = await aegis._conn.execute(
            "SELECT risk_score, prev_hash, signature FROM moskv_aegis_log"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == report["risk_score"]
        assert rows[0][1] == report["prev_hash"]
        assert rows[0][2] == report["signature"]

    @pytest.mark.asyncio
    async def test_cryptographic_chaining(self, aegis):
        """Successive runs should form a cryptographically chained prev_hash sequence."""
        r1 = await aegis.run_adversarial_audit()
        r2 = await aegis.run_adversarial_audit()

        # Verify signatures of r1 and r2 are valid
        assert aegis.verify_entry(r1, aegis.ledger.public_key) is True
        assert aegis.verify_entry(r2, aegis.ledger.public_key) is True

        # Verify that r2's prev_hash matches the computed entry_hash of r1
        import json
        import hashlib

        payload_obj = {
            "timestamp": r1["timestamp"],
            "risk_score": round(r1["risk_score"], 6),
            "findings": r1["findings"],
            "exploit_chains": r1["exploit_chains"],
            "prev_hash": r1["prev_hash"],
        }
        payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        expected_entry_hash = hashlib.sha256(payload_bytes).hexdigest()

        assert r2["prev_hash"] == expected_entry_hash
        assert r2["prev_hash"] != r1["signature"]

        # Verify from database order
        cursor = await aegis._conn.execute(
            "SELECT prev_hash, signature FROM moskv_aegis_log ORDER BY rowid ASC"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "GENESIS"
        assert rows[1][0] == expected_entry_hash
