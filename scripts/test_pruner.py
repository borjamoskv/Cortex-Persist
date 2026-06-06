import hashlib

from cortex.compaction.pruner import FactRecord, MerklePruner


def test_pruner():
    pruner = MerklePruner(tolerance_threshold=3)

    # Generate 5 mock facts
    facts = []
    for i in range(5):
        h = hashlib.sha256(f"fact_data_{i}".encode()).hexdigest()
        facts.append(
            FactRecord(
                id=f"fact_uuid_{i}",
                payload_hash=h,
                taint_token="taint:agent:abc",
                timestamp=f"2026-06-06T12:0{i}:00Z",
            )
        )

    seal = pruner.crystallize_snapshot(facts)
    assert seal is not None, "Snapshot failed"
    print(f"SEAL: {seal}")

    query = pruner.generate_purge_query(facts, seal)
    print("\n[PURGE QUERY]")
    print(query)


if __name__ == "__main__":
    test_pruner()
