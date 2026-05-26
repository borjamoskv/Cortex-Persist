"""CORTEX Context — VSA-SDM Adapter.

Wraps the sovereign VSA-SDM SwarmMemory into the ContextAssembler's
algebraic context interface. Replaces RAG-based retrieval with
deterministic hypervector cosine recall.

∴ Reality: C5-REAL (wraps verified VSA engine)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.context.vsa_adapter")

# Inject VSA engine path if not already importable
_VSA_SKILL_DIR = Path(__file__).parent.parent.parent / "skills" / "vsa-sdm-memory-omega"


def _ensure_vsa_importable() -> bool:
    """Add VSA skill dir to sys.path if needed.

    Returns True if the VSA engine is importable.
    """
    if _VSA_SKILL_DIR.exists() and str(_VSA_SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(_VSA_SKILL_DIR))

    try:
        import vsa_engine  # noqa: F401

        return True
    except ImportError:
        return False


class VSAContextAdapter:
    """Adapts SwarmMemory to ContextAssembler's query interface.

    Provides:
        - query(intent) → list[dict] for context retrieval
        - ingest(content, tags) → record to VSA memory
        - consolidate() → persist to disk (.vsa binary + SHA-256)

    Usage::

        adapter = VSAContextAdapter()
        results = adapter.query("deploy staging")
        adapter.ingest("deployed v2 to staging", tags={"env": "staging"})
        adapter.consolidate()
    """

    def __init__(
        self,
        agent_id: str = "cortex-pipeline",
        D: int = 10000,
        decay_lambda: float = 0.05,
        memory_dir: str | None = None,
    ):
        self._agent_id = agent_id
        self._D = D
        self._decay_lambda = decay_lambda
        self._memory_dir = memory_dir
        self._mem: Any | None = None
        self._available = _ensure_vsa_importable()

        if not self._available:
            logger.warning(
                "[VSA] VSA engine not importable (skill dir: %s). "
                "Algebraic context recall disabled.",
                _VSA_SKILL_DIR,
            )

    def _ensure_memory(self) -> Any | None:
        """Lazily initialize SwarmMemory."""
        if self._mem is not None:
            return self._mem

        if not self._available:
            return None

        try:
            from cortex_bridge import SwarmMemory

            kwargs: dict[str, Any] = {
                "agent_id": self._agent_id,
                "D": self._D,
                "decay_lambda": self._decay_lambda,
            }
            if self._memory_dir:
                kwargs["memory_dir"] = self._memory_dir

            self._mem = SwarmMemory(**kwargs)
            logger.info(
                "[VSA] SwarmMemory initialized: agent=%s D=%d",
                self._agent_id,
                self._D,
            )
            return self._mem

        except Exception as e:
            logger.warning("[VSA] SwarmMemory init failed: %s", e)
            self._available = False
            return None

    def query(self, intent: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Return top-k results from VSA algebraic recall.

        Args:
            intent: Natural language query.
            top_k: Maximum results to return.

        Returns:
            List of dicts with id, content, similarity, tags, timestamp.
            Empty list if VSA is unavailable or no matches above noise floor.
        """
        mem = self._ensure_memory()
        if mem is None:
            return []

        try:
            results = mem.recall_by_text(intent, top_k=top_k)
            return [
                {
                    "id": f"vsa-{i}",
                    "source": "vsa-sdm",
                    "content": text,
                    "similarity": round(sim, 4),
                    "tags": tags,
                    "timestamp": ts,
                }
                for i, (sim, text, tags, ts) in enumerate(results)
                if sim > 0.1  # Noise floor
            ]
        except Exception as e:
            logger.warning("[VSA] Query failed: %s", e)
            return []

    def ingest(self, content: str, tags: dict[str, str] | None = None) -> bool:
        """Record new content into VSA memory.

        Args:
            content: Free-text description to encode.
            tags: Optional structured metadata.

        Returns:
            True if successfully recorded.
        """
        mem = self._ensure_memory()
        if mem is None:
            return False

        try:
            mem.record_action(content, tags=tags)
            return True
        except Exception as e:
            logger.warning("[VSA] Ingest failed: %s", e)
            return False

    def consolidate(self) -> dict[str, Any]:
        """Persist memory tensor to disk.

        Returns:
            Consolidation report dict with path, bytes, items, etc.
        """
        mem = self._ensure_memory()
        if mem is None:
            return {"error": "VSA not available", "persisted": False}

        try:
            report = mem.consolidate()
            report["persisted"] = True
            return report
        except Exception as e:
            logger.warning("[VSA] Consolidation failed: %s", e)
            return {"error": str(e), "persisted": False}

    def diagnostics(self) -> dict[str, Any]:
        """Return VSA memory diagnostics."""
        mem = self._ensure_memory()
        if mem is None:
            return {"available": False}

        try:
            report = mem.diagnostics()
            report["available"] = True
            return report
        except Exception as e:
            return {"available": True, "error": str(e)}

    @property
    def is_available(self) -> bool:
        """Whether the VSA engine is importable and functional."""
        return self._available
