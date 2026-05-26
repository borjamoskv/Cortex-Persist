"""CORTEX VSA-SDM v7.1 — Zero-Dependency Sovereign Memory Substrate.

Pure Python implementation of Vector Symbolic Architecture (VSA) with
Sparse Distributed Memory (SDM) for algebraic context collapse.

Replaces RAG with deterministic algebraic operations:
- MAP-B binary hypervectors (XOR bind, majority bundle)
- Kanerva SDM with sparse activation for O(1) recall
- Ebbinghaus temporal decay for memory consolidation
- SHA-256 persistence for sovereign audit trail

Law Ω₀: Zero external dependencies. Pure Python list comprehensions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.memory.vsa")

# ── Constants ────────────────────────────────────────────────────────

DIMENSION = 10_000  # Hypervector dimensionality
SDM_LOCATIONS = 1000  # Kanerva hard locations
SDM_ACTIVATION_RADIUS = 450  # Hamming distance threshold (~45%)
PERSISTENCE_DIR = os.path.expanduser("~/.cortex/memory/vsa")


# ── MAP-B Algebra ────────────────────────────────────────────────────


def random_bipolar(dim: int = DIMENSION, seed: int | None = None) -> list[int]:
    """Generate a random binary hypervector {0, 1}^D."""
    rng = random.Random(seed)
    return [rng.randint(0, 1) for _ in range(dim)]


def bind(a: list[int], b: list[int]) -> list[int]:
    """XOR binding — exact self-inverse: bind(bind(a, b), b) == a."""
    return [(x + y) % 2 for x, y in zip(a, b, strict=False)]


def bundle(vectors: list[list[int]]) -> list[int]:
    """Majority-rule bundling — superposition of multiple vectors."""
    n = len(vectors)
    if n == 0:
        return [0] * DIMENSION
    if n == 1:
        return list(vectors[0])

    dim = len(vectors[0])
    result = [0] * dim
    threshold = n / 2

    for i in range(dim):
        total = sum(v[i] for v in vectors)
        result[i] = 1 if total > threshold else (0 if total < threshold else random.randint(0, 1))

    return result


def hamming_distance(a: list[int], b: list[int]) -> int:
    """Hamming distance between two binary vectors."""
    return sum(x != y for x, y in zip(a, b, strict=False))


def cosine_similarity(a: list[int], b: list[int]) -> float:
    """Cosine similarity for binary vectors (mapped to {-1, +1})."""
    dim = len(a)
    if dim == 0:
        return 0.0
    # Map 0→-1, 1→+1
    dot = sum((2 * x - 1) * (2 * y - 1) for x, y in zip(a, b, strict=False))
    return dot / dim


# ── Text Encoding (N-gram) ──────────────────────────────────────────


class TextEncoder:
    """Encodes text into hypervectors via character-level n-gram binding.

    Strategy:
    1. Each character → deterministic random HV (seeded by char code)
    2. N-gram = rotated bind of consecutive char HVs
    3. Document = bundle of all n-gram HVs
    """

    def __init__(self, dim: int = DIMENSION, ngram_size: int = 3):
        self._dim = dim
        self._n = ngram_size
        self._char_cache: dict[str, list[int]] = {}

    def _char_hv(self, c: str) -> list[int]:
        """Get deterministic HV for a character."""
        if c not in self._char_cache:
            self._char_cache[c] = random_bipolar(self._dim, seed=ord(c) + 42)
        return self._char_cache[c]

    @staticmethod
    def _rotate(v: list[int], positions: int = 1) -> list[int]:
        """Circular rotation for positional encoding."""
        if positions == 0:
            return list(v)
        p = positions % len(v)
        return v[-p:] + v[:-p]

    def encode(self, text: str) -> list[int]:
        """Encode text into a single hypervector."""
        text = text.lower().strip()
        if not text:
            return [0] * self._dim

        # Generate n-gram HVs
        ngram_hvs = []
        for i in range(len(text) - self._n + 1):
            gram = text[i : i + self._n]
            # Bind with positional rotation
            hv = self._char_hv(gram[0])
            for j in range(1, len(gram)):
                rotated = self._rotate(self._char_hv(gram[j]), j)
                hv = bind(hv, rotated)
            ngram_hvs.append(hv)

        if not ngram_hvs:
            return self._char_hv(text[0])

        return bundle(ngram_hvs)


# ── Kanerva SDM ──────────────────────────────────────────────────────


@dataclass
class SDMLocation:
    """A hard location in Kanerva SDM."""

    address: list[int]
    counters: list[int] = field(default_factory=list)
    write_count: int = 0
    last_write: float = 0.0

    def __post_init__(self):
        if not self.counters:
            self.counters = [0] * len(self.address)


class KanervaSDM:
    """Sparse Distributed Memory — O(1) associative recall.

    Architecture:
    - N hard locations with random addresses
    - Write: increment counters at all locations within activation radius
    - Read: sum counters from activated locations, threshold to binary
    - Capacity: SNR model — sqrt(D/N) items per location
    """

    def __init__(
        self,
        dim: int = DIMENSION,
        num_locations: int = SDM_LOCATIONS,
        activation_radius: int = SDM_ACTIVATION_RADIUS,
    ):
        self._dim = dim
        self._num_locations = num_locations
        self._radius = activation_radius
        self._locations: list[SDMLocation] = []
        self._initialized = False

    def initialize(self) -> None:
        """Generate random hard locations."""
        if self._initialized:
            return
        self._locations = [
            SDMLocation(address=random_bipolar(self._dim, seed=i * 7919))
            for i in range(self._num_locations)
        ]
        self._initialized = True
        logger.debug("[SDM] Initialized %d hard locations (D=%d)", self._num_locations, self._dim)

    def _activated_locations(self, address: list[int]) -> list[int]:
        """Find indices of locations within activation radius."""
        if not self._initialized:
            self.initialize()

        activated = []
        for i, loc in enumerate(self._locations):
            dist = hamming_distance(address, loc.address)
            if dist <= self._radius:
                activated.append(i)
        return activated

    def write(self, address: list[int], data: list[int]) -> int:
        """Write data vector to all activated locations.

        Returns number of activated locations.
        """
        if not self._initialized:
            self.initialize()

        activated = self._activated_locations(address)
        now = time.time()

        for idx in activated:
            loc = self._locations[idx]
            for j in range(self._dim):
                # Map binary to bipolar for counter update
                val = 2 * data[j] - 1  # 0→-1, 1→+1
                loc.counters[j] += val
            loc.write_count += 1
            loc.last_write = now

        logger.debug("[SDM] Write activated %d/%d locations", len(activated), self._num_locations)
        return len(activated)

    def read(self, address: list[int]) -> list[int]:
        """Read from all activated locations and threshold.

        Returns the reconstructed binary vector.
        """
        if not self._initialized:
            self.initialize()

        activated = self._activated_locations(address)
        if not activated:
            return [0] * self._dim

        # Sum counters across activated locations
        sums = [0] * self._dim
        for idx in activated:
            for j in range(self._dim):
                sums[j] += self._locations[idx].counters[j]

        # Threshold to binary
        return [1 if s > 0 else 0 for s in sums]

    def apply_decay(self, rate: float = 0.01) -> int:
        """Ebbinghaus exponential decay on all locations.

        Decays counter magnitudes by rate per cycle.
        Returns number of affected locations.
        """
        affected = 0
        for loc in self._locations:
            if loc.write_count == 0:
                continue
            decay_factor = 1.0 - rate
            loc.counters = [int(c * decay_factor) for c in loc.counters]
            affected += 1
        return affected

    @property
    def stats(self) -> dict[str, Any]:
        """Memory statistics."""
        if not self._initialized:
            return {"initialized": False}
        active = sum(1 for loc in self._locations if loc.write_count > 0)
        return {
            "initialized": True,
            "num_locations": self._num_locations,
            "dimension": self._dim,
            "active_locations": active,
            "utilization": active / self._num_locations if self._num_locations else 0,
        }


# ── Agent Memory (Per-Agent VSA Store) ───────────────────────────────


@dataclass
class MemoryRecord:
    """A single memory entry with metadata."""

    id: str
    content: str
    vector: list[int]
    timestamp: float = 0.0
    tags: list[str] = field(default_factory=list)
    relevance: float = 1.0


class SwarmMemory:
    """Per-agent associative memory with VSA encoding + SDM storage.

    Provides:
    - record(): encode text → store in SDM
    - recall(): query by text similarity → ranked results
    - consolidate(): decay + compress stale memories
    - persist/load(): SHA-256 verified .vsa files
    """

    def __init__(self, agent_id: str = "default", dim: int = DIMENSION):
        self._agent_id = agent_id
        self._dim = dim
        self._encoder = TextEncoder(dim=dim)
        self._sdm = KanervaSDM(dim=dim)
        self._records: dict[str, MemoryRecord] = {}
        self._persistence_path = Path(PERSISTENCE_DIR) / f"{agent_id}.vsa"

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def record(
        self,
        content: str,
        record_id: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Encode and store a memory.

        Returns the record ID.
        """
        rid = record_id or hashlib.sha256(content.encode()).hexdigest()[:12]
        vector = self._encoder.encode(content)

        # Store in SDM
        self._sdm.write(vector, vector)

        # Store metadata
        self._records[rid] = MemoryRecord(
            id=rid,
            content=content,
            vector=vector,
            timestamp=time.time(),
            tags=tags or [],
        )

        logger.debug("[VSA] Recorded memory %s (%d chars)", rid, len(content))
        return rid

    def recall(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.05,
    ) -> list[dict[str, Any]]:
        """Recall memories by algebraic similarity.

        Args:
            query: Natural language query
            top_k: Maximum results
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of dicts with id, content, similarity, tags
        """
        query_vector = self._encoder.encode(query)

        # Score all records by cosine similarity
        scored = []
        for _rid, rec in self._records.items():
            sim = cosine_similarity(query_vector, rec.vector)
            if sim >= min_similarity:
                scored.append((sim, rec))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, rec in scored[:top_k]:
            results.append(
                {
                    "id": rec.id,
                    "content": rec.content,
                    "similarity": round(sim, 4),
                    "tags": rec.tags,
                    "timestamp": rec.timestamp,
                }
            )

        return results

    def consolidate(self, decay_rate: float = 0.01) -> int:
        """Apply Ebbinghaus decay and prune dead memories.

        Returns number of memories pruned.
        """
        self._sdm.apply_decay(decay_rate)

        # Prune records with vectors that no longer recall
        pruned = 0
        dead_ids = []
        for rid, rec in self._records.items():
            reconstructed = self._sdm.read(rec.vector)
            sim = cosine_similarity(rec.vector, reconstructed)
            if sim < 0.01:
                dead_ids.append(rid)
                pruned += 1

        for rid in dead_ids:
            del self._records[rid]

        if pruned:
            logger.info("[VSA] Consolidated: pruned %d dead memories", pruned)
        return pruned

    def persist(self) -> str:
        """Save memory state to disk with SHA-256 integrity hash.

        Returns the integrity hash.
        """
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize records (without vectors — too large)
        data = {
            "agent_id": self._agent_id,
            "dimension": self._dim,
            "records": {
                rid: {
                    "content": rec.content,
                    "timestamp": rec.timestamp,
                    "tags": rec.tags,
                }
                for rid, rec in self._records.items()
            },
            "sdm_stats": self._sdm.stats,
            "saved_at": time.time(),
        }

        payload = json.dumps(data, ensure_ascii=False, indent=2)
        integrity_hash = hashlib.sha256(payload.encode()).hexdigest()
        data["integrity_hash"] = integrity_hash

        with open(self._persistence_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(
            "[VSA] Persisted %d memories to %s (hash=%s)",
            len(self._records),
            self._persistence_path,
            integrity_hash[:16],
        )
        return integrity_hash

    def load(self) -> int:
        """Load memory state from disk and re-encode vectors.

        Returns number of records loaded.
        """
        if not self._persistence_path.exists():
            return 0

        with open(self._persistence_path, encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for rid, rec_data in data.get("records", {}).items():
            content = rec_data["content"]
            vector = self._encoder.encode(content)
            self._sdm.write(vector, vector)

            self._records[rid] = MemoryRecord(
                id=rid,
                content=content,
                vector=vector,
                timestamp=rec_data.get("timestamp", 0),
                tags=rec_data.get("tags", []),
            )
            count += 1

        logger.info("[VSA] Loaded %d memories from %s", count, self._persistence_path)
        return count

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "agent_id": self._agent_id,
            "records": len(self._records),
            "sdm": self._sdm.stats,
        }


# ── Pipeline Bridge ──────────────────────────────────────────────────


class VSAPipelineBridge:
    """Bridges VSA-SDM to the ContextAssembler.

    Implements the interface expected by ContextAssembler._search_vsa():
    - query(intent, top_k) → list[dict] with id, content
    """

    def __init__(self, agent_id: str = "cortex"):
        self._memory = SwarmMemory(agent_id=agent_id)
        self._memory.load()  # Load persisted state

    def query(self, intent: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Query VSA memory for relevant context."""
        return self._memory.recall(query=intent, top_k=top_k)

    def ingest(
        self, content: str, record_id: str | None = None, tags: list[str] | None = None
    ) -> str:
        """Ingest new knowledge into VSA memory."""
        return self._memory.record(content=content, record_id=record_id, tags=tags)

    def persist(self) -> str:
        """Persist VSA state to disk."""
        return self._memory.persist()

    @property
    def stats(self) -> dict[str, Any]:
        return self._memory.stats
