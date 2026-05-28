"""Tests for Crypto-Shredding Engine — Phase 2."""

import sqlite3

import pytest

from cortex.crypto.shredder import CryptoShredder


@pytest.fixture
def db():
    """In-memory SQLite with facts table."""
    conn = sqlite3.Connection(":memory:")
    conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            project TEXT,
            source TEXT,
            tenant_id TEXT DEFAULT 'default'
        )
    """)
    conn.execute(
        "INSERT INTO facts (id, content, project, source) VALUES (1, 'secret data', 'test', 'user:alice')"
    )
    conn.execute(
        "INSERT INTO facts (id, content, project, source) VALUES (2, 'more data', 'test', 'user:alice')"
    )
    conn.execute(
        "INSERT INTO facts (id, content, project, source) VALUES (3, 'other data', 'test', 'user:bob')"
    )
    conn.commit()
    return conn


class TestCryptoShredder:
    """Crypto-shredding tests (sync API)."""

    def test_shred_single_fact(self, db):
        shredder = CryptoShredder(db)
        result = shredder.shred_fact(1)
        assert result.success
        assert not result.was_already_shredded
        assert shredder.is_shredded(1)

    def test_shred_already_shredded(self, db):
        shredder = CryptoShredder(db)
        shredder.shred_fact(1)
        result = shredder.shred_fact(1)
        assert result.success
        assert result.was_already_shredded

    def test_is_shredded_false(self, db):
        shredder = CryptoShredder(db)
        assert not shredder.is_shredded(999)

    def test_get_shredded_ids(self, db):
        shredder = CryptoShredder(db)
        shredder.shred_fact(1)
        shredder.shred_fact(3)
        ids = shredder.get_shredded_fact_ids()
        assert ids == {1, 3}

    def test_shred_with_reason(self, db):
        shredder = CryptoShredder(db)
        result = shredder.shred_fact(1, reason="user_request", shredded_by="admin")
        assert result.success
        assert result.reason == "user_request"

    def test_audit_shredding(self, db):
        shredder = CryptoShredder(db)
        shredder.shred_fact(1, reason="gdpr_erasure")
        shredder.shred_fact(2, reason="gdpr_erasure")
        shredder.shred_fact(3, reason="project_erasure")

        audit = shredder.audit_shredding()
        assert audit["total_shredded"] == 3
        assert audit["compliant"]
        assert "gdpr_erasure" in audit["by_reason"]
        assert audit["by_reason"]["gdpr_erasure"]["count"] == 2

    def test_empty_audit(self, db):
        shredder = CryptoShredder(db)
        audit = shredder.audit_shredding()
        assert audit["total_shredded"] == 0
        assert audit["compliant"]
