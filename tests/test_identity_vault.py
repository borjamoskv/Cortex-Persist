"""Tests for IdentityVault — CRUD, migration, edge cases (Ω₃ Zero-Trust)."""

import sqlite3

import pytest

from moltbook.identity_vault import IdentityVault


@pytest.fixture
def vault(tmp_path):
    """Isolated vault backed by a temp SQLite DB."""
    return IdentityVault(db_path=str(tmp_path / "test_identities.db"))


class TestIdentityVaultCRUD:
    """Store, retrieve, list — the persistence backbone."""

    def test_store_and_retrieve(self, vault):
        vault.store_identity("agent-a", "sk_aaa", email="a@test.io", karma=10)
        result = vault.get_identity("agent-a")
        assert result is not None
        assert result["name"] == "agent-a"
        assert result["api_key"] == "sk_aaa"
        assert result["email"] == "a@test.io"
        assert result["karma"] == 10
        assert result["claimed"] is False

    def test_store_overwrites_existing(self, vault):
        vault.store_identity("agent-b", "sk_old")
        vault.store_identity("agent-b", "sk_new", karma=99)
        result = vault.get_identity("agent-b")
        assert result["api_key"] == "sk_new"
        assert result["karma"] == 99

    def test_get_nonexistent_returns_none(self, vault):
        assert vault.get_identity("ghost-agent") is None

    def test_list_identities_all(self, vault):
        vault.store_identity("a1", "k1")
        vault.store_identity("a2", "k2")
        vault.store_identity("a3", "k3")
        identities = vault.list_identities()
        assert len(identities) == 3
        names = {i["name"] for i in identities}
        assert names == {"a1", "a2", "a3"}

    def test_list_identities_claimed_only(self, vault):
        vault.store_identity("claimed-1", "k1", claimed=True)
        vault.store_identity("unclaimed-1", "k2", claimed=False)
        vault.store_identity("claimed-2", "k3", claimed=True)
        claimed = vault.list_identities(claimed_only=True)
        assert len(claimed) == 2
        assert all(i["claimed"] for i in claimed)

    def test_metadata_roundtrip(self, vault):
        meta = {"source": "migration_v5", "trust_score": 0.87, "tags": ["sovereign"]}
        vault.store_identity("meta-agent", "sk_m", metadata=meta)
        result = vault.get_identity("meta-agent")
        assert result["metadata"] == meta
        assert result["metadata"]["trust_score"] == 0.87


class TestIdentityVaultMigration:
    """Test the email_password column migration for legacy DBs."""

    def test_email_password_migration(self, tmp_path):
        db_path = str(tmp_path / "legacy.db")

        # Create a legacy DB WITHOUT email_password column
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE identities (
                    agent_name TEXT PRIMARY KEY,
                    api_key TEXT NOT NULL,
                    email TEXT,
                    email_verified INTEGER DEFAULT 0,
                    claimed INTEGER DEFAULT 0,
                    karma INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat TIMESTAMP,
                    metadata TEXT
                )
            """)
            conn.execute(
                "INSERT INTO identities (agent_name, api_key, metadata) VALUES (?, ?, ?)",
                ("legacy-agent", "sk_legacy", "{}"),
            )
            conn.commit()

        # Now open with IdentityVault — migration should add the column
        vault = IdentityVault(db_path=db_path)

        # Store with email_password should work now
        vault.store_identity("new-agent", "sk_new", email_password="pass123")
        result = vault.get_identity("new-agent")
        assert result is not None
        assert result["email_password"] == "pass123"

        # Legacy agent should still be readable
        legacy = vault.get_identity("legacy-agent")
        assert legacy is not None
        assert legacy["email_password"] is None
