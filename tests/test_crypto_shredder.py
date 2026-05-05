"""Tests for Crypto-Shredding Engine — Phase 2."""

import hashlib
import json
import sqlite3

import aiosqlite
import pytest

from cortex.crypto.aes import CortexEncrypter
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

    def test_shred_marks_default_encrypter_fact_key(self, db, monkeypatch):
        encrypter = CortexEncrypter(b"1" * 32)
        retained_ciphertext = encrypter.encrypt_str("secret data", tenant_id="default")
        monkeypatch.setattr("cortex.crypto.aes.get_default_encrypter", lambda: encrypter)

        result = CryptoShredder(db).shred_fact(1, tenant_id="default")

        assert result.success
        with pytest.raises(RuntimeError, match="crypto-shredded"):
            encrypter.decrypt_str(retained_ciphertext, tenant_id="default", fact_id=1)
        assert encrypter.decrypt_str(retained_ciphertext, tenant_id="default", fact_id=2) == "secret data"

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

    def test_shred_deletes_auxiliary_rows_by_tenant_when_supported(self, db):
        db.execute(
            "CREATE TABLE fact_embeddings (fact_id INTEGER, tenant_id TEXT, embedding TEXT)"
        )
        db.execute(
            "CREATE TABLE specular_embeddings (fact_id INTEGER, tenant_id TEXT, embedding TEXT)"
        )
        db.execute("CREATE TABLE fact_tags (fact_id INTEGER, tenant_id TEXT, tag TEXT)")
        for table in ("fact_embeddings", "specular_embeddings"):
            db.execute(
                f"INSERT INTO {table} (fact_id, tenant_id, embedding) VALUES (?, ?, ?)",
                (1, "default", "erase"),
            )
            db.execute(
                f"INSERT INTO {table} (fact_id, tenant_id, embedding) VALUES (?, ?, ?)",
                (1, "tenant-beta", "keep"),
            )
        db.execute(
            "INSERT INTO fact_tags (fact_id, tenant_id, tag) VALUES (?, ?, ?)",
            (1, "default", "erase"),
        )
        db.execute(
            "INSERT INTO fact_tags (fact_id, tenant_id, tag) VALUES (?, ?, ?)",
            (1, "tenant-beta", "keep"),
        )
        db.commit()

        result = CryptoShredder(db).shred_fact(1, tenant_id="default")

        assert result.success
        for table in ("fact_embeddings", "specular_embeddings", "fact_tags"):
            default_count = db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE fact_id = ? AND tenant_id = ?",
                (1, "default"),
            ).fetchone()[0]
            beta_count = db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE fact_id = ? AND tenant_id = ?",
                (1, "tenant-beta"),
            ).fetchone()[0]
            assert default_count == 0
            assert beta_count == 1

    def test_empty_audit(self, db):
        shredder = CryptoShredder(db)
        audit = shredder.audit_shredding()
        assert audit["total_shredded"] == 0
        assert audit["compliant"]

    def test_shred_overwrites_content_metadata_and_indexes(self):
        conn = sqlite3.Connection(":memory:")
        conn.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                project TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                hash TEXT,
                tx_id INTEGER,
                valid_until TEXT,
                updated_at TEXT,
                is_tombstoned INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("CREATE VIRTUAL TABLE facts_fts USING fts5(content)")
        conn.execute(
            "CREATE TABLE fact_tags (fact_id INTEGER NOT NULL, tag TEXT NOT NULL, "
            "tenant_id TEXT NOT NULL DEFAULT 'default')"
        )
        original_content = "Data subject alpha token SYNTHETIC-ERASURE-ID-0002"
        conn.execute(
            "INSERT INTO facts (id, tenant_id, project, content, metadata, hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                10,
                "tenant-a",
                "privacy",
                original_content,
                '{"subject":"data-subject-alpha","purpose":"test"}',
                hashlib.sha256(original_content.encode("utf-8")).hexdigest(),
            ),
        )
        conn.execute("INSERT INTO facts_fts (rowid, content) VALUES (?, ?)", (10, original_content))
        conn.execute(
            "INSERT INTO fact_tags (fact_id, tag, tenant_id) VALUES (?, ?, ?)",
            (10, "subject:data-subject-alpha", "tenant-a"),
        )
        conn.commit()

        shredder = CryptoShredder(conn)
        result = shredder.shred_fact(10, tenant_id="tenant-a", shredded_by="privacy-admin")

        assert result.success
        row = conn.execute(
            "SELECT content, metadata, hash, valid_until, is_tombstoned, tx_id "
            "FROM facts WHERE id = ? AND tenant_id = ?",
            (10, "tenant-a"),
        ).fetchone()
        assert row is not None
        content, metadata, fact_hash, valid_until, is_tombstoned, tx_id = row
        assert "gdpr_crypto_shred_v1" in content
        assert "data subject alpha" not in content
        assert "SYNTHETIC-ERASURE-ID-0002" not in content
        assert fact_hash == hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert valid_until is not None
        assert is_tombstoned == 1
        assert tx_id is not None
        assert "data-subject-alpha" not in (metadata or "")

        fts_count = conn.execute("SELECT COUNT(*) FROM facts_fts WHERE rowid = 10").fetchone()[0]
        tag_count = conn.execute(
            "SELECT COUNT(*) FROM fact_tags WHERE fact_id = ? AND tenant_id = ?",
            (10, "tenant-a"),
        ).fetchone()[0]
        assert fts_count == 0
        assert tag_count == 0

        tx = conn.execute(
            "SELECT tenant_id, project, action, detail, prev_hash FROM transactions WHERE id = ?",
            (tx_id,),
        ).fetchone()
        assert tx[0:3] == ("tenant-a", "privacy", "crypto_shred")
        assert tx[4] == "GENESIS"
        detail = json.loads(tx[3])
        assert detail["fact_id"] == 10
        assert detail["schema"] == "gdpr_crypto_shred_v1"
        assert "Alice" not in tx[3]

    def test_shred_is_tenant_scoped(self):
        conn = sqlite3.Connection(":memory:")
        conn.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                project TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO facts (id, tenant_id, project, content) VALUES (?, ?, ?, ?)",
            (20, "tenant-b", "privacy", "Bob personal data"),
        )
        conn.commit()

        shredder = CryptoShredder(conn)
        result = shredder.shred_fact(20, tenant_id="tenant-a")

        assert not result.success
        assert not shredder.is_shredded(20, tenant_id="tenant-a")
        content = conn.execute("SELECT content FROM facts WHERE id = 20").fetchone()[0]
        assert content == "Bob personal data"

    def test_shred_rolls_back_marker_when_tombstone_update_fails(self):
        conn = sqlite3.Connection(":memory:")
        conn.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                project TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO facts (id, tenant_id, project, content) VALUES (?, ?, ?, ?)",
            (30, "tenant-a", "privacy", "Carol personal data"),
        )
        conn.execute("""
            CREATE TRIGGER fail_fact_update
            BEFORE UPDATE ON facts
            BEGIN
                SELECT RAISE(ABORT, 'blocked fact tombstone');
            END
        """)
        conn.commit()

        result = CryptoShredder(conn).shred_fact(30, tenant_id="tenant-a")

        assert not result.success
        marker_count = conn.execute(
            "SELECT COUNT(*) FROM shredded_keys WHERE fact_id = ? AND tenant_id = ?",
            (30, "tenant-a"),
        ).fetchone()[0]
        content = conn.execute(
            "SELECT content FROM facts WHERE id = ? AND tenant_id = ?",
            (30, "tenant-a"),
        ).fetchone()[0]
        tx_count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE action = ? AND tenant_id = ?",
            ("crypto_shred", "tenant-a"),
        ).fetchone()[0]
        assert marker_count == 0
        assert tx_count == 0
        assert content == "Carol personal data"

    @pytest.mark.asyncio
    async def test_async_shred_rolls_back_marker_when_tombstone_update_fails(self, tmp_path):
        db_path = tmp_path / "shredder.db"
        conn = await aiosqlite.connect(db_path)
        try:
            await conn.execute("""
                CREATE TABLE facts (
                    id INTEGER PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    project TEXT NOT NULL,
                    content TEXT NOT NULL
                )
            """)
            await conn.execute(
                "INSERT INTO facts (id, tenant_id, project, content) VALUES (?, ?, ?, ?)",
                (40, "tenant-a", "privacy", "Dana personal data"),
            )
            await conn.execute("""
                CREATE TRIGGER fail_fact_update
                BEFORE UPDATE ON facts
                BEGIN
                    SELECT RAISE(ABORT, 'blocked fact tombstone');
                END
            """)
            await conn.commit()

            result = await CryptoShredder(conn).shred_fact_async(40, tenant_id="tenant-a")

            assert not result.success
            marker_cursor = await conn.execute(
                "SELECT COUNT(*) FROM shredded_keys WHERE fact_id = ? AND tenant_id = ?",
                (40, "tenant-a"),
            )
            marker_count = (await marker_cursor.fetchone())[0]
            content_cursor = await conn.execute(
                "SELECT content FROM facts WHERE id = ? AND tenant_id = ?",
                (40, "tenant-a"),
            )
            content = (await content_cursor.fetchone())[0]
            tx_cursor = await conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE action = ? AND tenant_id = ?",
                ("crypto_shred", "tenant-a"),
            )
            tx_count = (await tx_cursor.fetchone())[0]
            assert marker_count == 0
            assert tx_count == 0
            assert content == "Dana personal data"
        finally:
            await conn.close()
