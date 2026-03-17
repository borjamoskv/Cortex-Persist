"""
CORTEX V6 - Holographic Memory (Vector 2 of the Singularity).

Maintains a RAM-resident mapping of the Sovereign Vector Store.
Bypasses SQLite and I/O latency for background swarm (Heartbeat) context retrieval
using heavily optimized NumPy matrix operations (O(1) inherent retrieval).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional, TYPE_CHECKING

import numpy as np

from cortex.memory.models import CortexFactModel

if TYPE_CHECKING:
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

logger = logging.getLogger("cortex.memory.hologram")


class HolographicMemory:
    """RAM-resident semantic memory map for zero-latency CORTEX retrieval."""

    __slots__ = (
        "_store",
        "_lock",
        "_tensor",
        "_metadata",
        "_tenant_idx",
        "_project_idx",
        "_ready",
        "_half_life",
    )

    def __init__(self, store: SovereignVectorStoreL2, half_life_days: int = 7):
        self._store = store
        self._lock = asyncio.Lock()

        # Matrix E containing all embeddings (N, dimension).
        self._tensor: Optional[np.ndarray] = None

        # Parallel arrays for fast metadata lookup and scoring
        self._metadata: list[dict[str, Any]] = []

        # Hash indexes for filtering
        self._tenant_idx: dict[str, set[int]] = {}
        self._project_idx: dict[str, set[int]] = {}

        self._ready = False
        self._half_life = half_life_days * 24 * 3600

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def initialize(self) -> None:
        """Load the entire memory surface into the RAM hologram."""
        async with self._lock:
            if self._ready:
                return

            logger.info("🌌 Initializing Holographic Memory matrix...")
            start_time = time.monotonic()

            # Access underlying DB directly to bypass async overhead for initial load
            conn = self._store._get_conn()

            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    m.rowid, m.id, m.tenant_id, m.project_id, m.content, m.timestamp,
                    m.is_diamond, m.is_bridge, m.confidence, m.success_rate,
                    m.cognitive_layer, m.parent_decision_id, m.metadata,
                    v.embedding
                FROM facts_meta m
                JOIN vec_facts v ON m.rowid = v.rowid
            """)

            rows = cursor.fetchall()

            embeddings = []
            for i, row in enumerate(rows):
                emb = np.frombuffer(row["embedding"], dtype=np.float32)
                embeddings.append(emb)

                tenant = row["tenant_id"]
                project = row["project_id"]

                # Metadata record
                meta_record = {
                    "id": row["id"],
                    "tenant_id": tenant,
                    "project_id": project,
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "is_diamond": bool(row["is_diamond"]),
                    "is_bridge": bool(row["is_bridge"]),
                    "confidence": row["confidence"],
                    "success_rate": row["success_rate"],
                    "cognitive_layer": row["cognitive_layer"] or "semantic",
                    "parent_decision_id": row["parent_decision_id"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
                self._metadata.append(meta_record)

                # Indexes
                if tenant not in self._tenant_idx:
                    self._tenant_idx[tenant] = set()
                self._tenant_idx[tenant].add(i)

                if project not in self._project_idx:
                    self._project_idx[project] = set()
                self._project_idx[project].add(i)

            if embeddings:
                # Pre-normalize for pure dot product cosine similarity
                E_raw = np.vstack(embeddings)
                norms = np.linalg.norm(E_raw, axis=1, keepdims=True)
                norms[norms == 0] = 1.0  # Avoid division by zero
                self._tensor = E_raw / norms
            else:
                self._tensor = np.empty((0, self._store._encoder.dimension), dtype=np.float32)

            self._ready = True
            dur = (time.monotonic() - start_time) * 1000

            logger.info(
                "🌌 Holographic Memory loaded: %d items mapped in %.1fms", len(self._metadata), dur
            )

    def _cortex_decay(self, is_diamond: bool, timestamp: float, current_time: float) -> float:
        """Physical decay calculation in Python space."""
        if is_diamond:
            return 1.0
        age = max(0.0, current_time - timestamp)
        return float((0.5) ** (age / self._half_life))

    async def recall_holographic(
        self,
        query: str,
        limit: int = 5,
        tenant_id: str = "default",
        project_id: Optional[str] = None,
        layer: Optional[str] = None,
    ) -> list[CortexFactModel]:
        """[VECTOR-2] Zero-Friction O(1) recall from RAM hologram."""
        if not self._ready:
            await self.initialize()

        if self._tensor is None or self._tensor.shape[0] == 0:
            return []

        # 1. Encode query (We still need the ML model, but no DB I/O)
        query_vector = await self._store._encoder.encode(query)
        q = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        # 2. Filter mask
        valid_indices = self._tenant_idx.get(tenant_id, set())
        if project_id:
            proj_idx = self._project_idx.get(project_id, set())

            # Allow bridge items seamlessly
            bridge_idx = {i for i in valid_indices if self._metadata[i]["is_bridge"]}
            valid_indices = valid_indices.intersection(proj_idx).union(bridge_idx)

        if not valid_indices:
            return []

        # Convert to sorted array for subsetting
        indices_list = np.array(list(valid_indices), dtype=int)

        # 3. Dense Matrix Math - Hardware Accelerated
        subset_tensor = self._tensor[indices_list]
        cosine_sim = np.dot(subset_tensor, q)

        # 4. Map similarity + decay + OUROBOROS success rate
        final_scores = []
        now = time.time()
        for i, original_idx in enumerate(indices_list):
            meta = self._metadata[original_idx]

            if layer and meta["cognitive_layer"] != layer:
                final_scores.append(-1.0)
                continue

            sim = cosine_sim[i]
            # Match the SQLite function structure exactly
            decay = self._cortex_decay(meta["is_diamond"], meta["timestamp"], now)

            # Translate SQL semantic: (1.0 - distance / 2.0) equals (sim + 1.0) / 2.0
            semantic_score = (sim + 1.0) / 2.0
            final_score = semantic_score * decay * meta["success_rate"]

            final_scores.append(final_score)

        final_scores_arr = np.array(final_scores)
        top_k_subset_idx = np.argsort(final_scores_arr)[::-1]

        results = []
        for subset_idx in top_k_subset_idx:
            sc = float(final_scores_arr[subset_idx])
            if sc <= 0.0:
                break

            if len(results) >= limit:
                break

            orig_idx = indices_list[subset_idx]
            meta = self._metadata[orig_idx]

            # Construct FactModel (Embedding retrieval omitted to save memory copies during fast context injection)
            fact = CortexFactModel(
                id=meta["id"],
                tenant_id=meta["tenant_id"],
                project_id=meta["project_id"],
                content=meta["content"],
                embedding=[],  # We skip vector reconstruction to keep it absolutely fast
                timestamp=meta["timestamp"],
                is_diamond=meta["is_diamond"],
                is_bridge=meta["is_bridge"],
                confidence=meta["confidence"],
                cognitive_layer=meta["cognitive_layer"],
                parent_decision_id=meta["parent_decision_id"],
                metadata=meta["metadata"],
            )
            object.__setattr__(fact, "_recall_score", sc)
            results.append(fact)

        return results
