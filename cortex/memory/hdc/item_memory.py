"""CORTEX v7 — HDC Item Memory (Codebook).

Deterministic mapping of atomic symbols (tokens, roles, projects)
to random bipolar hypervectors. Uses seeded RNG for reproducibility:
    same symbol → same hypervector across sessions.

The codebook is lazy-loaded and persisted to JSON for cold-start speed.

Architecture:
    - Role vectors: one per CORTEX fact type (decision, bridge, ghost, ...)
    - Project vectors: one per project name
    - Token vectors: one per unique word/bigram (auto-generated on first use)
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Final

import numpy as np

from cortex.memory.hdc.algebra import DEFAULT_DIM, HVType, cosine_similarity, random_bipolar

__all__ = ["ItemMemory"]

logger = logging.getLogger("cortex.memory.hdc.item_memory")

# Sovereign fact types from CORTEX ontology
CORTEX_ROLES: Final[tuple[str, ...]] = (
    "axiom",
    "bridge",
    "config",
    "decision",
    "error",
    "evolution",
    "general",
    "ghost",
    "intent",
    "knowledge",
    "meta_learning",
    "phantom",
    "report",
    "research",
    "rule",
    "schema",
    "task",
    "test",
    "world-model",
)


def _deterministic_seed(symbol: str) -> int:
    """Derive a deterministic integer seed from a symbol string.

    Uses SHA-256 truncated to 8 bytes → 64-bit integer.
    Guarantees same symbol always produces same hypervector.
    """
    digest = hashlib.sha256(symbol.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big")


class ItemMemory:
    """Codebook mapping symbols to deterministic bipolar hypervectors.

    All vectors are generated lazily and cached. The codebook can be
    saved to / loaded from disk for sub-100ms cold starts.

    Args:
        dim: Hypervector dimensionality (default: 10,000).
        codebook_path: Optional path for persistent codebook JSON.
    """

    __slots__ = ("_cache", "_dim", "_codebook_path")

    def __init__(
        self,
        dim: int = DEFAULT_DIM,
        codebook_path: str | Path | None = None,
    ) -> None:
        self._dim = dim
        self._cache: dict[str, HVType] = {}
        self._codebook_path = Path(codebook_path) if codebook_path else None

        if self._codebook_path and self._codebook_path.exists():
            self._load_codebook()

        # Pre-generate role vectors for all CORTEX fact types
        for role in CORTEX_ROLES:
            self._get_or_create(f"role:{role}")

    def encode(self, symbol: str) -> HVType:
        """Get or create the hypervector for a symbol.

        Args:
            symbol: Any string key (token, role:type, project:name).

        Returns:
            Deterministic bipolar hypervector for this symbol.
        """
        return self._get_or_create(symbol)

    def role_vector(self, fact_type: str) -> HVType:
        """Get the role hypervector for a CORTEX fact type.

        Args:
            fact_type: One of CORTEX_ROLES (decision, bridge, ghost, ...).

        Returns:
            Role hypervector.
        """
        return self._get_or_create(f"role:{fact_type}")

    def project_vector(self, project: str) -> HVType:
        """Get the project hypervector.

        Args:
            project: Project name (e.g., 'cortex', 'naroa-2026').

        Returns:
            Project hypervector.
        """
        return self._get_or_create(f"project:{project}")

    def nearest(
        self, query_hv: HVType, candidates: list[str] | None = None, top_k: int = 1
    ) -> list[tuple[str, float]]:
        """Find the nearest symbols to a query hypervector.

        Args:
            query_hv: The hypervector to search for.
            candidates: Optional subset of symbols to search.
                        If None, searches the entire codebook.
            top_k: Number of results to return.

        Returns:
            List of (symbol, similarity) tuples sorted by similarity (desc).
        """
        search_space = candidates or list(self._cache.keys())
        scores: list[tuple[str, float]] = []

        for symbol in search_space:
            if symbol not in self._cache:
                continue
            sim = cosine_similarity(query_hv, self._cache[symbol])
            scores.append((symbol, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def save_codebook(self) -> None:
        """Persist the codebook to disk as JSON (int8 → list[int])."""
        if not self._codebook_path:
            return

        self._codebook_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "dim": self._dim,
            "vectors": {k: v.tolist() for k, v in self._cache.items()},
        }
        self._codebook_path.write_text(json.dumps(data), encoding="utf-8")
        logger.info(
            "HDC codebook saved: %d symbols, dim=%d → %s",
            len(self._cache),
            self._dim,
            self._codebook_path,
        )

    @property
    def dim(self) -> int:
        """Hypervector dimensionality."""
        return self._dim

    @property
    def size(self) -> int:
        """Number of symbols in the codebook."""
        return len(self._cache)

    # ─── Private ──────────────────────────────────────────────────

    def _get_or_create(self, symbol: str) -> HVType:
        """Get from cache or generate deterministically."""
        if symbol not in self._cache:
            seed = _deterministic_seed(symbol)
            self._cache[symbol] = random_bipolar(self._dim, seed=seed)
        return self._cache[symbol]

    def _load_codebook(self) -> None:
        """Load codebook from JSON file."""
        if not self._codebook_path or not self._codebook_path.exists():
            return

        try:
            raw = json.loads(self._codebook_path.read_text(encoding="utf-8"))
            saved_dim = raw.get("dim", self._dim)
            if saved_dim != self._dim:
                logger.warning(
                    "Codebook dim mismatch: saved=%d, current=%d. Regenerating.",
                    saved_dim,
                    self._dim,
                )
                return

            vectors = raw.get("vectors", {})
            for k, v in vectors.items():
                self._cache[k] = np.array(v, dtype=np.int8)

            logger.info(
                "HDC codebook loaded: %d symbols from %s",
                len(self._cache),
                self._codebook_path,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to load HDC codebook: %s", exc)
