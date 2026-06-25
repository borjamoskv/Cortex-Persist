# [C5-REAL] Exergy-Maximized
from legacy_research.types.models import UniversalMemorySchema


def test_universal_memory_schema_validation():
    valid_payload = {
        "ums_version": "1.0.0",
        "header": {
            "agent_did": "did:cortex:0x0a0a0a0a",
            "owner_did": "did:eth:0x2b3be5",
            "transaction_id": "tx_01h9a",
            "timestamp": 1779864525,
        },
        "payload": {
            "block_id": "blk_8829",
            "type": "retrieval_belief",
            "content": "User rejects TailwindCSS. Enforce Vanilla CSS.",
            "confidence": 0.992,
            "vector_reference": {
                "hash": "sha256:e3b0c442",
                "dimensions": 1536,
            },
            "thermodynamics": {
                "stochastic_entropy_in": 12.4,
                "deterministic_exergy_out": 110.8,
                "half_life_seconds": 2592000,
            },
        },
        "proof": {
            "zk_merkle_root": "0x5c8e",
            "signature": "0x4b3a",
        },
    }
    schema = UniversalMemorySchema(**valid_payload)
    assert schema.ums_version == "1.0.0"
    assert schema.header.agent_did == "did:cortex:0x0a0a0a0a"
    assert schema.payload.thermodynamics.deterministic_exergy_out == 110.8
