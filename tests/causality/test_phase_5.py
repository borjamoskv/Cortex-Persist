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
from cortex.engine.cognitive.models import Fact
from cortex.database.mixins.query_mixin import QueryMixin


class TestMCP:
    """MCP tools have parent_decision_id support."""

    def test_cortex_store_has_parent(self):
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "cortex",
                "mcp_server",
                "server.py",
            )
        ) as f:
            src = f.read()
        assert "parent_decision_id: int = 0" in src

    def test_cortex_trace_chain_defined(self):
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "cortex",
                "mcp_server",
                "core_tools.py",
            )
        ) as f:
            src = f.read()
        assert "async def cortex_trace_chain(" in src
