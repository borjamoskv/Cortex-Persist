"""Runtime Capabilities — Sovereign Capability Detection (Axiom Ω₁₃)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("cortex.engine.capabilities")


@dataclass(frozen=True)
class RuntimeCapabilities:
    """System capability matrix."""

    ledger_write: bool
    embeddings: bool
    vector_index: bool
    causal_tracing: bool
    oracle_verify: bool
    degraded_mode: bool


class CapabilityRegistry:
    """Registry for detecting and tracking CORTEX capabilities."""

    _instance: Optional[CapabilityRegistry] = None

    def __init__(self):
        self._caps = self._detect_initial_capabilities()

    @classmethod
    def get_instance(cls) -> CapabilityRegistry:
        if cls._instance is None:
            cls._instance = CapabilityRegistry()
        return cls._instance

    @property
    def capabilities(self) -> RuntimeCapabilities:
        return self._caps

    def _detect_initial_capabilities(self) -> RuntimeCapabilities:
        """Heuristic detection of available subsystems."""
        no_embed = os.getenv("CORTEX_NO_EMBED", "false").lower() == "true"

        # Check embeddings without importing torch
        # We check if sentence-transformers is in the environment
        # but avoid loading it here.
        has_embeddings = not no_embed
        try:
            import importlib.util

            if importlib.util.find_spec("sentence_transformers") is None:
                has_embeddings = False
        except Exception:
            has_embeddings = False

        # Vector index (sqlite-vec)
        has_vector = True
        try:
            # This is a light check
            import sqlite3

            sqlite3.connect(":memory:")
            # We don't load the extension yet, just check if we want to
            if os.getenv("CORTEX_NO_VEC", "false").lower() == "true":
                has_vector = False
        except Exception:
            has_vector = False

        is_degraded = no_embed or not has_vector

        return RuntimeCapabilities(
            ledger_write=True,  # Foundation is always True
            embeddings=has_embeddings,
            vector_index=has_vector,
            causal_tracing=True,  # Logic based, usually available
            oracle_verify=True,  # Logic based
            degraded_mode=is_degraded,
        )

    def refresh(self):
        """Force re-detection of capabilities."""
        self._caps = self._detect_initial_capabilities()


from typing import Optional
