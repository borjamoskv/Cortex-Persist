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

from babylon60.engine.fact_store_core import insert_fact_record
from babylon60.engine.mixins.base import FACT_COLUMNS
from babylon60.engine.models import Fact
from babylon60.engine.query_mixin import QueryMixin


class TestCLI:
    """CLI commands have correct params."""

    def test_store_has_parent_flag(self):
        from babylon60.cli.memory_cmds import store

        params = {p.name for p in store.params}
        assert "parent_id" in params

    def test_trace_chain_exists(self):
        from babylon60.cli.causal_cmds import trace_chain

        params = {p.name for p in trace_chain.params}
        assert "fact_id" in params
        assert "direction" in params
        assert "depth" in params
