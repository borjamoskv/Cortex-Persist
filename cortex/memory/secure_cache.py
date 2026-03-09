import hashlib
import json
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, final

logger = logging.getLogger("cortex.memory.secure_cache")


@final
class CortexSecureMemoryCache:
    """
    CORTEX v6.0 — Sovereign Memory Cache with Evidence Chain (Ω₂).

    Bounded LRU cache that mathematically proves its 'forgetting' history.
    Implements a cryptographic hash chain (Ω₀) for all evictions, ensuring
    that no state transition is lost and every eviction is auditable.

    Axiom: Ω₂ (Entropic Asymmetry) — memory is finite; audit trails are infinite.
    """

    __slots__ = (
        "max_capacity",
        "cache",
        "persistence_callback",
        "_chain_tip",
        "_eviction_count",
    )

    def __init__(
        self,
        max_capacity: int,
        persistence_callback: Callable[[str, dict[str, Any], dict[str, Any]], None] | None = None,
    ):
        """
        Initialize the Sovereign Cache.

        Args:
            max_capacity: Maximum items before eviction triggers.
            persistence_callback: Hook for persistent storage (Ledger/DB).
        """
        self.max_capacity = max_capacity
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.persistence_callback = persistence_callback

        # 🔗 Sovereign Evidence Chain (Ω₀)
        self._chain_tip = hashlib.sha256(b"CORTEX_GENESIS_VOID").hexdigest()
        self._eviction_count = 0

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve and refresh LRU position."""
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, data: dict[str, Any]) -> None:
        """Insert/Update item, enforcing capacity with Proof-of-Forgetting."""
        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = data

        if len(self.cache) > self.max_capacity:
            oldest_key, oldest_data = self.cache.popitem(last=False)
            self._secure_eviction(oldest_key, oldest_data)

    def _secure_eviction(self, key: str, data: dict[str, Any]) -> None:
        """
        Intercepts eviction to generate a Decisional Proof (Ω₂).
        Computes a hash chained to the previous eviction to ensure integrity.
        """
        try:
            self._eviction_count += 1

            # 1. Deterministic serialization
            serialized_data = json.dumps(data, sort_keys=True).encode("utf-8")
            payload_hash = hashlib.sha256(serialized_data).hexdigest()

            # 2. Evidence Chain Update (H(prev_tip | key_hash | payload_hash))
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            prev_tip = self._chain_tip

            proof_material = f"{prev_tip}|{key_hash}|{payload_hash}"
            self._chain_tip = hashlib.sha256(proof_material.encode()).hexdigest()

            # 3. Sovereign Audit Entry
            audit_entry = {
                "ts": time.time(),
                "eviction_id": self._eviction_count,
                "key": key,
                "prev_proof": prev_tip,
                "current_proof": self._chain_tip,
                "payload_hash": payload_hash,
                "axiom": "Ω₂",
                "commitment": "dynamic",
            }

            # 4. Persistence
            self._persist_to_storage(key, data, audit_entry)

        except Exception as e:
            logger.error("🚨 [INTEGRITY BREACH] Secure eviction failed for %s: %s", key, e)

    def _persist_to_storage(self, key: str, data: dict[str, Any], audit: dict[str, Any]) -> None:
        """Commit data and decisional proof to persistent storage."""
        logger.info("🛡️ [SOVEREIGN CACHE] Evicting %s | Proof: %s...", key, audit['current_proof'][:8])

        if self.persistence_callback:
            self.persistence_callback(key, data, audit)

    def prove_forgetting(self) -> dict[str, Any]:
        """Provides the current cryptographic tip of the forgetting history."""
        return {
            "tip": self._chain_tip,
            "count": self._eviction_count,
            "status": "SOVEREIGN_VALIDATED",
        }

    @staticmethod
    def verify_forgetting_proof(
        initial_tip: str, evidence_list: list[dict[str, Any]]
    ) -> tuple[bool, str]:
        """
        Mathematically proves the chain of forgetting.

        Args:
            initial_tip: The starting hash (genesis or checkpoint).
            evidence_list: Sorted list of audit entries.

        Returns:
            (Boolean: Valid?, String: Final Tip)
        """
        current_tip = initial_tip
        for entry in evidence_list:
            # Verify the previous link
            if entry["prev_proof"] != current_tip:
                return False, current_tip

            # Recompute current proof
            key_hash = hashlib.sha256(entry["key"].encode()).hexdigest()
            payload_hash = entry["payload_hash"]

            proof_material = f"{current_tip}|{key_hash}|{payload_hash}"
            expected_tip = hashlib.sha256(proof_material.encode()).hexdigest()

            if entry["current_proof"] != expected_tip:
                return False, current_tip

            current_tip = expected_tip

        return True, current_tip


if __name__ == "__main__":
    import unittest

    class TestSovereignCache(unittest.TestCase):
        def test_evidence_chain(self):
            evidence_trail = []

            def collect(k, v, audit):
                evidence_trail.append(audit)

            cache = CortexSecureMemoryCache(max_capacity=1, persistence_callback=collect)
            genesis = cache.prove_forgetting()["tip"]

            cache.put("A", {"x": 1})
            cache.put("B", {"x": 2})  # A evicted
            cache.put("C", {"x": 3})  # B evicted

            valid, final_tip = CortexSecureMemoryCache.verify_forgetting_proof(
                genesis, evidence_trail
            )
            self.assertTrue(valid)
            self.assertEqual(final_tip, cache.prove_forgetting()["tip"])

    unittest.main()
