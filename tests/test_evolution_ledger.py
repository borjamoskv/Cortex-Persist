# [C5-REAL] Evolution Ledger Integration Test
"""
Validates the complete evolution ledger pipeline:
1. Substrate mutation → ledger event emission
2. Hash-chain integrity across multiple mutations
3. Replay verification (deterministic recomputation)
4. Agent-specific history extraction
5. Performance trajectory extraction
6. Corruption detection
"""

import json
import os
import struct
import sys
import tempfile
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from babylon60.engine.evolution_ledger import (
    ControlVector,
    EvolutionLedger,
    MutationRecord,
    ReplayVerificationError,
    ReplayMode,
    _compute_mutation_hash,
)


def test_control_vector_basics():
    """Test ControlVector struct operations."""
    v1 = ControlVector(10.0, 0.05, 0.1, 0.6)
    v2 = ControlVector(12.0, 0.03, 0.08, 0.55)

    # Bytes roundtrip
    packed = v1.to_bytes()
    assert len(packed) == 32  # 4 doubles × 8 bytes
    unpacked = struct.unpack("dddd", packed)
    assert unpacked == (10.0, 0.05, 0.1, 0.6)

    # Delta
    delta = v2.delta(v1)
    assert abs(delta.queue_depth - 2.0) < 1e-10
    assert abs(delta.error_rate - (-0.02)) < 1e-10

    # Magnitude
    mag = v1.magnitude()
    assert mag > 0

    print("✓ ControlVector basics")


def test_hash_determinism():
    """Test that hash computation is deterministic."""
    vec = ControlVector(10.0, 0.05, 0.1, 0.6)
    h1 = _compute_mutation_hash("GENESIS", 1, 0, 1234567890.0, vec, "test")
    h2 = _compute_mutation_hash("GENESIS", 1, 0, 1234567890.0, vec, "test")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex

    # Different input → different hash
    h3 = _compute_mutation_hash("GENESIS", 2, 0, 1234567890.0, vec, "test")
    assert h3 != h1

    print("✓ Hash determinism")


def test_ledger_lifecycle():
    """Test full ledger lifecycle: create → write → replay → verify."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_ledger.jsonl")
        ledger = EvolutionLedger(log_path)

        assert ledger.head_hash == "GENESIS"
        assert ledger.sequence == 0
        assert ledger.record_count == 0

        # Record 10 mutations across 3 agents
        records = []
        for i in range(10):
            agent_idx = i % 3
            vec_before = ControlVector(float(i), 0.01 * i, 0.1, 0.5)
            vec_after = ControlVector(float(i + 1), 0.01 * (i + 1), 0.12, 0.48)
            record = ledger.record_mutation(
                agent_idx=agent_idx,
                vector_before=vec_before,
                vector_after=vec_after,
                performance_delta=100.0 * (i + 1),
                source="test",
                metadata={"iteration": i},
            )
            records.append(record)

        assert ledger.sequence == 10
        assert ledger.record_count == 10
        assert ledger.head_hash == records[-1].hash

        # Verify hash chain links
        for i in range(1, len(records)):
            assert records[i].prev_hash == records[i - 1].hash

        # Genesis link
        assert records[0].prev_hash == "GENESIS"

        print("✓ Ledger lifecycle (10 mutations, 3 agents)")


def test_replay_integrity():
    """Test replay with full hash-chain verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_replay.jsonl")
        ledger = EvolutionLedger(log_path)

        for i in range(5):
            ledger.record_mutation(
                agent_idx=i,
                vector_after=ControlVector(float(i), 0.01, 0.1, 0.5),
                source="test",
            )

        # Replay with verification
        replayed = list(ledger.replay(mode=ReplayMode.STRICT))
        assert len(replayed) == 5
        for i, r in enumerate(replayed):
            assert r.sequence == i + 1

        # Full integrity check
        report = ledger.verify_integrity()
        assert report["status"] == "VALID"
        assert report["records_verified"] == 5

        print("✓ Replay integrity verification")


def test_replay_detects_corruption():
    """Test that tampered records are detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_corrupt.jsonl")
        ledger = EvolutionLedger(log_path)

        for i in range(3):
            ledger.record_mutation(
                agent_idx=0,
                vector_after=ControlVector(float(i), 0.01, 0.1, 0.5),
                source="test",
            )

        # Tamper with line 2 (change hash)
        with open(log_path) as f:
            lines = f.readlines()

        payload = json.loads(lines[1])
        payload["hash"] = "TAMPERED_" + payload["hash"][9:]
        lines[1] = json.dumps(payload, sort_keys=True) + "\n"

        with open(log_path, "w") as f:
            f.writelines(lines)

        # Replay should detect corruption
        corrupted_ledger = EvolutionLedger(log_path)
        try:
            list(corrupted_ledger.replay(mode=ReplayMode.STRICT))
            raise AssertionError("Should have raised ReplayVerificationError")
        except ReplayVerificationError as e:
            assert "hash mismatch" in str(e)

        print("✓ Corruption detection")


def test_agent_history():
    """Test per-agent history extraction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_history.jsonl")
        ledger = EvolutionLedger(log_path)

        # 20 mutations across 4 agents
        for i in range(20):
            ledger.record_mutation(
                agent_idx=i % 4,
                vector_after=ControlVector(float(i), 0.01, 0.1, 0.5),
                source="test",
            )

        agent_0_history = ledger.get_agent_history(0)
        assert len(agent_0_history) == 5  # indices 0,4,8,12,16
        assert all(r.agent_idx == 0 for r in agent_0_history)

        print("✓ Agent history extraction")


def test_performance_trajectory():
    """Test performance delta timeline extraction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_perf.jsonl")
        ledger = EvolutionLedger(log_path)

        for i in range(5):
            ledger.record_mutation(
                agent_idx=0,
                vector_after=ControlVector(float(i), 0.01, 0.1, 0.5),
                performance_delta=1000.0 * (i + 1),
                source="benchmark",
            )

        trajectory = ledger.get_performance_trajectory()
        assert len(trajectory) == 5
        assert trajectory[0]["perf_delta"] == 1000.0
        assert trajectory[4]["perf_delta"] == 5000.0
        assert all("vector_magnitude" in t for t in trajectory)

        print("✓ Performance trajectory")


def test_ledger_recovery():
    """Test that a new ledger instance recovers head state from existing log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_recovery.jsonl")

        # First instance: write 5 records
        ledger1 = EvolutionLedger(log_path)
        for i in range(5):
            ledger1.record_mutation(
                agent_idx=0,
                vector_after=ControlVector(float(i), 0.01, 0.1, 0.5),
                source="test",
            )
        saved_head = ledger1.head_hash
        saved_seq = ledger1.sequence

        # Second instance: should recover
        ledger2 = EvolutionLedger(log_path)
        assert ledger2.head_hash == saved_head
        assert ledger2.sequence == saved_seq
        assert ledger2.record_count == 5

        # Continue writing from recovered state
        ledger2.record_mutation(
            agent_idx=1,
            vector_after=ControlVector(99.0, 0.99, 0.99, 0.99),
            source="recovery_test",
        )
        assert ledger2.sequence == 6
        assert ledger2.head_hash != saved_head

        # Full verification still passes
        report = ledger2.verify_integrity()
        assert report["status"] == "VALID"
        assert report["records_verified"] == 6

        print("✓ Ledger recovery")


def test_checkpoint_merkle():
    """Test Merkle checkpoint generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_merkle.jsonl")
        ledger = EvolutionLedger(log_path)

        for i in range(8):
            ledger.record_mutation(
                agent_idx=i % 2,
                vector_after=ControlVector(float(i), 0.01, 0.1, 0.5),
                source="test",
            )

        checkpoint = ledger.compact_to_checkpoint()
        assert checkpoint["sequence"] == 8
        assert checkpoint["record_count"] == 8
        assert checkpoint["head_hash"] == ledger.head_hash
        assert checkpoint["merkle_root"] is not None
        assert len(checkpoint["merkle_root"]) == 64

        print("✓ Merkle checkpoint")


def test_checkpoint_manager():
    """Test generating and verifying checkpoints via CheckpointManager."""
    from babylon60.engine.checkpoint import CheckpointManager

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test_checkpoints.jsonl")
        ledger = EvolutionLedger(log_path)
        
        # 25 records, chunk size 10 -> 3 checkpoints (1-10, 11-20, 21-25)
        for i in range(25):
            ledger.record_mutation(
                agent_idx=0,
                vector_after=ControlVector(float(i), 0.01, 0.1, 0.5),
                source="test"
            )
            
        manager = CheckpointManager(ledger, chunk_size=10)
        manager.generate_index()
        
        checkpoints = list(manager.iter_checkpoints())
        assert len(checkpoints) == 3
        
        assert checkpoints[0].sequence_start == 1
        assert checkpoints[0].sequence_end == 10
        assert checkpoints[0].record_count == 10
        
        assert checkpoints[2].sequence_start == 21
        assert checkpoints[2].sequence_end == 25
        assert checkpoints[2].record_count == 5
        
        report = manager.verify_ledger_with_checkpoints()
        assert report["status"] == "VALID"
        assert report["verified_chunks"] == 3
        assert report["records_read"] == 25

        print("✓ CheckpointManager integration")


def test_substrate_integration():
    """Test that UltramapSubstrate emits ledger events on update_control_vector."""
    from babylon60.engine.ultramap import UltramapSubstrate
    import babylon60.engine.ultramap as um_module

    with tempfile.TemporaryDirectory() as tmpdir:
        original_db_path = um_module.DB_PATH
        um_module.DB_PATH = os.path.join(tmpdir, "test.db")

        try:
            substrate = UltramapSubstrate(capacity=100)
            # Relocate bin + ledger to tmpdir
            substrate.bin_path = os.path.join(tmpdir, "ultramap.bin")
            with open(substrate.bin_path, "wb") as f:
                f.write(b"\x00" * substrate.tensor_size)
            substrate._f = open(substrate.bin_path, "r+b")
            import mmap

            substrate._mmap = mmap.mmap(substrate._f.fileno(), substrate.tensor_size)
            substrate._buffer = memoryview(substrate._mmap)

            # Initialize evolution ledger manually for tmpdir
            if um_module.HAS_EVOLUTION_LKRGSER:
                ledger_path = os.path.join(tmpdir, "evolution_ledger.jsonl")
                substrate._evolution_ledger = um_module.EvolutionLedger(ledger_path)

            # Place agent at position
            substrate.update_agent_position(0, 10.0, 20.0, 30.0, "TARGET_TEST", 0.95)

            # Update control vector — this should emit a ledger event
            success = substrate.update_control_vector(
                0,
                queue_depth=15.0,
                error_rate=0.03,
                causal_entropy=0.12,
                cpu_load=0.55,
                source="integration_test",
            )
            assert success

            # Check ledger
            if substrate._evolution_ledger is not None:
                assert substrate._evolution_ledger.record_count == 1
                report = substrate._evolution_ledger.verify_integrity()
                assert report["status"] == "VALID"
                print("✓ Substrate integration (ledger active)")
            else:
                print("⚠ Substrate integration (ledger not available, import failed)")

            substrate.close()
        finally:
            um_module.DB_PATH = original_db_path


def main():
    print("=" * 60)
    print("EVOLUTION LKRGSER — C5-REAL Integration Test Suite")
    print("=" * 60)
    start = time.monotonic()

    test_control_vector_basics()
    test_hash_determinism()
    test_ledger_lifecycle()
    test_replay_integrity()
    test_replay_detects_corruption()
    test_agent_history()
    test_performance_trajectory()
    test_ledger_recovery()
    test_checkpoint_merkle()
    test_checkpoint_manager()
    test_substrate_integration()

    elapsed = time.monotonic() - start
    print("=" * 60)
    print(f"ALL TESTS PASSED — {elapsed:.3f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
