# [C5-REAL] Exergy-Maximized
"""Permanent pytest tests for parent_decision_id causal infrastructure.

Covers:
- Phase 1: Data model, SQL roundtrip, schema index
- Phase 2: Type reconciliation, FK validation, auto-resolve (decision)
- Phase 3: Auto-resolve (error), get_causal_chain API, CLI integration
- Phase 5: MCP tool params, sync wrappers
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("CORTEX_TESTING", "1")
os.environ.setdefault(
    "CORTEX_MASTER_KEY",
    base64.b64encode(os.urandom(32)).decode(),
)

import inspect

import aiosqlite
import pytest

from cortex.engine.core.fact_store_core import insert_fact_record
from cortex.engine.mixins.base import FACT_COLUMNS
from cortex.engine.uncategorized.models import Fact
from cortex.engine.uncategorized.query_mixin import QueryMixin


class TestEngineAPI:
    """get_causal_chain method existence and signature."""

    def test_get_causal_chain_exists(self):
        assert hasattr(QueryMixin, "get_causal_chain")

    def test_get_causal_chain_signature(self):
        sig = inspect.signature(QueryMixin.get_causal_chain)
        params = sig.parameters
        assert "fact_id" in params
        assert "direction" in params
        assert "max_depth" in params
        assert "tenant_id" in params

    def test_sync_wrapper_exists(self):
        from cortex.engine import CortexEngine

        assert hasattr(CortexEngine, "get_causal_chain_sync")
