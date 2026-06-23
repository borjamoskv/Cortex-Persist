# [C5-REAL] Exergy-Maximized
import pytest
import hashlib
import sqlite3
import aiosqlite
from unittest.mock import MagicMock
from babylon60.ledger.ledger_core import MerkleTree, SovereignLedger


def test_merkle_tree_root():
    """Validates Merkle Tree root calculation for simple cases."""
    leaves = [hashlib.sha256(b"a").hexdigest(), hashlib.sha256(b"b").hexdigest()]
    tree = MerkleTree(leaves)

    expected_root = hashlib.sha256((leaves[0] + leaves[1]).encode()).hexdigest()
    assert tree.root_hash == expected_root


def test_merkle_tree_odd_leaves():
    """Validates Merkle Tree root calculation with odd number of leaves (duplication)."""
    leaves = [hashlib.sha256(b"a").hexdigest()]
    tree = MerkleTree(leaves)
    assert tree.root_hash == leaves[0]

    leaves3 = [
        hashlib.sha256(b"a").hexdigest(),
        hashlib.sha256(b"b").hexdigest(),
        hashlib.sha256(b"c").hexdigest(),
    ]
    tree3 = MerkleTree(leaves3)
    # L1: [a, b, c, c]
    # L2: [H(a+b), H(c+c)]
    # L3: [H(H(a+b)+H(c+c))]
    h_ab = hashlib.sha256((leaves3[0] + leaves3[1]).encode()).hexdigest()
    h_cc = hashlib.sha256((leaves3[2] + leaves3[2]).encode()).hexdigest()
    expected_root = hashlib.sha256((h_ab + h_cc).encode()).hexdigest()
    assert tree3.root_hash == expected_root


def test_merkle_tree_proof():
    """Validates Merkle Tree proof generation and verification."""
    leaves = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(4)]
    tree = MerkleTree(leaves)
    root = tree.root_hash

    for i in range(4):
        proof = tree.get_proof(i)
        assert MerkleTree.verify_proof(leaves[i], proof, root) is True

    # Invalid proof
    assert MerkleTree.verify_proof(leaves[0], [], root) is False
    assert MerkleTree.verify_proof(leaves[0], tree.get_proof(1), root) is False


def test_sovereign_ledger_sync_ops(tmp_path):
    """Validates synchronous SovereignLedger transaction recording and integrity."""
    db_path = tmp_path / "ledger.db"
    conn = sqlite3.connect(db_path)
    ledger = SovereignLedger(conn)

    # Genesis
    h1 = ledger.record_transaction("proj", "action1", {"data": 1}, tenant_id="t1")
    assert h1 is not None

    # Follow-up
    h2 = ledger.record_transaction("proj", "action2", {"data": 2}, tenant_id="t1")
    assert h2 is not None

    # Verify chain in DB
    cursor = conn.execute(
        "SELECT prev_hash, hash FROM transactions WHERE tenant_id='t1' ORDER BY id"
    )
    rows = cursor.fetchall()
    assert rows[0][0] == "GENESIS"
    assert rows[0][1] == h1
    assert rows[1][0] == h1
    assert rows[1][1] == h2


def test_sovereign_ledger_checkpoint(tmp_path):
    """Validates Merkle checkpoint creation in SovereignLedger."""
    db_path = tmp_path / "checkpoint.db"
    conn = sqlite3.connect(db_path)
    ledger = SovereignLedger(conn)

    # Need to reach batch_size for checkpoint. Default is 100 if low rate, but let's mock it
    # or just use a small batch size if we can influence it.
    # SovereignLedger.adaptive_batch_size depends on _config.
    mock_config = MagicMock()
    mock_config.CHECKPOINT_MAX = 2
    ledger._config = mock_config

    ledger.record_transaction("p", "a", "d")
    ledger.record_transaction("p", "a", "d")

    root = ledger.create_checkpoint()
    assert root is not None

    cursor = conn.execute("SELECT root_hash FROM merkle_roots WHERE tx_count=2")
    row = cursor.fetchone()
    assert row[0] == root


@pytest.mark.asyncio
async def test_sovereign_ledger_async_ops(tmp_path):
    """Validates asynchronous SovereignLedger operations."""
    db_path = tmp_path / "async_ledger.db"
    async with aiosqlite.connect(db_path) as conn:
        # We need to manually init schema because SovereignLedger init only does it for sync
        ledger = SovereignLedger(conn)

        # Manually create schema for async test (or use a helper if available)
        # ledger._ensure_schema_sync(MagicMock()) # This needs a sync conn

        # For the purpose of this test, let's just run the SQL
        with sqlite3.connect(db_path) as s_conn:
            ledger._ensure_schema_sync(s_conn)

        h1 = await ledger.record_transaction_async("p", "a", {"val": 10}, tenant_id="t2")
        assert h1 is not None

        # Verify integrity
        report = await ledger.audit_integrity_async(tenant_id="t2")
        assert report["valid"] is True
        assert report["tx_count"] == 1
