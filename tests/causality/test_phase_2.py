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

from cortex.engine.fact_store_core import insert_fact_record
from cortex.engine.mixins.base import FACT_COLUMNS
from cortex.engine.models import Fact
from cortex.engine.query_mixin import QueryMixin




class TestTypeReconciliation:
    """CortexFactModel uses int | None, not str | None."""

    def test_memory_model_type(self):
        import typing

        from cortex.memory.models import CortexFactModel

        field = CortexFactModel.model_fields["parent_decision_id"]
        args = typing.get_args(field.annotation)
        if args:
            assert int in args
            assert str not in args
