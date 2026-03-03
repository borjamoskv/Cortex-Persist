"""
Test file for verifying storage-layer immutability (Axiom Ω₃) for Procedural Engrams.
Specifically tests that the permanent flag cannot transition from 1 to 0.
"""

import sqlite3

import pytest

from cortex.database.schema import get_all_schema


@pytest.fixture
def memory_db():
    """In-memory SQLite database initialized with all CORTEX schemas."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    # Load all schema extensions, including CREATE_PROCEDURAL_ENGRAMS
    for statement in get_all_schema():
        try:
            cur.executescript(statement)
        except Exception:
            pass  # ignore virtual tables missing dependencies in raw minimal test

    yield conn
    conn.close()


def test_procedural_engram_immutability(memory_db):
    """Test that a permanent=1 procedural engram cannot be downgraded to permanent=0."""
    cur = memory_db.cursor()

    # 1. Insert a temporary record
    cur.execute(
        "INSERT INTO procedural_engrams (skill_name, last_invoked, permanent) VALUES (?, ?, ?)",
        ("skill_alpha", 0.0, 0),
    )
    memory_db.commit()

    # 2. Update to permanent=1 (Valid)
    try:
        cur.execute("UPDATE procedural_engrams SET permanent = 1 WHERE skill_name = 'skill_alpha'")
        memory_db.commit()
    except sqlite3.Error as e:
        pytest.fail(f"Failed to upgrade skill to permanent: {e}")

    # Verify it became permanent
    cur.execute("SELECT permanent FROM procedural_engrams WHERE skill_name = 'skill_alpha'")
    assert cur.fetchone()[0] == 1

    # 3. Attempt to downgrade to permanent=0 (Should Fail)
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        cur.execute("UPDATE procedural_engrams SET permanent = 0 WHERE skill_name = 'skill_alpha'")
        memory_db.commit()

    assert "Immunitas-Omega" in str(exc_info.value)

    # Verify it remained permanent
    cur.execute("SELECT permanent FROM procedural_engrams WHERE skill_name = 'skill_alpha'")
    assert cur.fetchone()[0] == 1


def test_procedural_engram_insert_permanent(memory_db):
    """Test that we can insert a permanent record immediately."""
    cur = memory_db.cursor()

    # 1. Insert a permanent record
    cur.execute(
        "INSERT INTO procedural_engrams (skill_name, last_invoked, permanent) VALUES (?, ?, ?)",
        ("skill_omega", 0.0, 1),
    )
    memory_db.commit()

    # 2. Attempt to downgrade to permanent=0 (Should Fail)
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        cur.execute("UPDATE procedural_engrams SET permanent = 0 WHERE skill_name = 'skill_omega'")
        memory_db.commit()

    assert "Immunitas-Omega" in str(exc_info.value)

    # Verify it remained permanent
    cur.execute("SELECT permanent FROM procedural_engrams WHERE skill_name = 'skill_omega'")
    assert cur.fetchone()[0] == 1
