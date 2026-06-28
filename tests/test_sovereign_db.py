# [C5-REAL] Exergy-Maximized
"""Tests for cortex.database.sovereign_db.

Validates:
- Concurrent writes
- Concurrent reads
- Rollback execution
- Deadlock resilience under simulated load
- Cursor features (fetchall, fetchone, async iteration)
- Error handling (invalid SQL, closed db programming errors)
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path

import pytest

from cortex.database.sovereign_db import SovereignDB, SovereignCursor


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Provide a path to a temporary SQLite database."""
    return str(tmp_path / "test_sovereign.db")


@pytest.fixture
async def db(db_path: str):
    """Provide an initialized SovereignDB instance, closed after test."""
    async with SovereignDB(db_path) as conn:
        # Create a basic test table
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name TEXT NOT NULL,"
            "  balance REAL NOT NULL"
            ")"
        )
        yield conn


# ─── Lifecycle & Basic Ops ─────────────────────────────────────────────


class TestBasicOperations:
    async def test_execute_insert_and_select(self, db: SovereignDB):
        # Insert test
        cursor = await db.execute(
            "INSERT INTO users (name, balance) VALUES (?, ?)", ("Alice", 100.0)
        )
        assert cursor.lastrowid is not None
        assert cursor.lastrowid > 0
        assert cursor.rowcount == 1

        # Select test
        cursor = await db.execute("SELECT name, balance FROM users WHERE name = ?", ("Alice",))
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0] == ("Alice", 100.0)

        # Check description
        assert cursor.description is not None
        assert cursor.description[0][0] == "name"
        assert cursor.description[1][0] == "balance"

    async def test_fetchone(self, db: SovereignDB):
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("Alice", 100.0))
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("Bob", 200.0))

        cursor = await db.execute("SELECT name FROM users ORDER BY name")
        assert cursor.fetchone() == ("Alice",)
        assert cursor.fetchone() == ("Bob",)
        assert cursor.fetchone() is None

    async def test_async_iteration(self, db: SovereignDB):
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("Alice", 100.0))
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("Bob", 200.0))

        cursor = await db.execute("SELECT name FROM users ORDER BY name")
        results = []
        async for row in cursor:
            results.append(row)

        assert results == [("Alice",), ("Bob",)]

    async def test_execute_many(self, db: SovereignDB):
        data = [("Alice", 150.0), ("Bob", 250.0), ("Charlie", 350.0)]
        cursor = await db.execute_many("INSERT INTO users (name, balance) VALUES (?, ?)", data)
        assert cursor.rowcount == 3

        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = cursor.fetchone()
        assert row[0] == 3

    async def test_invalid_sql_raises(self, db: SovereignDB):
        with pytest.raises(sqlite3.OperationalError):
            await db.execute("INSERT INTO nonexistent_table (foo) VALUES (1)")

    async def test_programming_error_after_close(self, db_path: str):
        conn = SovereignDB(db_path)
        await conn.close()

        with pytest.raises(sqlite3.ProgrammingError):
            await conn.execute("SELECT 1")

        # Double close should be a safe no-op
        await conn.close()


# ─── Transactions & Rollback ───────────────────────────────────────────


class TestTransactions:
    async def test_commit_saves_changes(self, db: SovereignDB):
        # By default in DEFERRED mode, sqlite3 implicitly starts transactions.
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("TxUser", 50.0))
        await db.commit()

        # Check in a new database connection
        async with SovereignDB(db.database_path) as db2:
            res = await db2.execute("SELECT COUNT(*) FROM users WHERE name = ?", ("TxUser",))
            assert res.fetchone()[0] == 1

    async def test_rollback_undoes_changes(self, db: SovereignDB):
        # Standard insert
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("Permanent", 90.0))
        await db.commit()

        # Insert to be rolled back
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("Temporary", 10.0))
        await db.rollback()

        # Insert after rollback
        await db.execute(
            "INSERT INTO users (name, balance) VALUES (?, ?)", ("SecondPermanent", 80.0)
        )
        await db.commit()

        # Verify results
        res = await db.execute("SELECT name FROM users ORDER BY name")
        names = [r[0] for r in res.fetchall()]
        assert "Permanent" in names
        assert "SecondPermanent" in names
        assert "Temporary" not in names


# ─── Concurrency & Deadlocks ───────────────────────────────────────────


class TestConcurrencyAndDeadlocks:
    async def test_concurrent_writes(self, db: SovereignDB):
        # Run 20 concurrent inserts using asyncio.gather
        num_tasks = 20

        async def insert_task(index: int):
            await db.execute(
                "INSERT INTO users (name, balance) VALUES (?, ?)", (f"User_{index}", float(index))
            )

        await asyncio.gather(*[insert_task(i) for i in range(num_tasks)])

        res = await db.execute("SELECT COUNT(*) FROM users")
        assert res.fetchone()[0] == num_tasks

    async def test_concurrent_reads(self, db: SovereignDB):
        # Insert a few rows first
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("A", 1.0))
        await db.execute("INSERT INTO users (name, balance) VALUES (?, ?)", ("B", 2.0))
        await db.commit()

        # Run 50 concurrent read tasks
        num_tasks = 50

        async def read_task():
            cursor = await db.execute("SELECT name, balance FROM users ORDER BY name")
            rows = cursor.fetchall()
            assert len(rows) == 2
            assert rows[0][0] == "A"
            assert rows[1][0] == "B"

        await asyncio.gather(*[read_task() for _ in range(num_tasks)])

    async def test_deadlock_resilience(self, db: SovereignDB):
        """Simulate heavy concurrent write and read transactions to verify deadlock resilience under load.

        Under WAL mode and normalized busy_timeout, concurrent reads and writes
        should complete without raising database locked errors or deadlocking.
        """
        import random

        num_tasks = 40

        async def worker(index: int):
            # Mix of reads and writes with minor random yield to simulate natural contention
            await asyncio.sleep(random.uniform(0.001, 0.01))
            if index % 2 == 0:
                # Write operation
                await db.execute(
                    "INSERT INTO users (name, balance) VALUES (?, ?)",
                    (f"Concurrent_{index}", 50.0 + index),
                )
                await db.commit()
            else:
                # Read operation
                cursor = await db.execute("SELECT COUNT(*) FROM users")
                cursor.fetchall()

        # Trigger all tasks concurrently
        await asyncio.gather(*[worker(i) for i in range(num_tasks)])

        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        # At least 20 writes should have succeeded (the even indices)
        assert count >= 20
