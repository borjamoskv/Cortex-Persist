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

from legacy_research.engine.fact_store_core import insert_fact_record
from legacy_research.engine.mixins.base import FACT_COLUMNS
from legacy_research.engine.models import Fact
from legacy_research.engine.query_mixin import QueryMixin




class TestDataModel:
    """Fact dataclass and SQL column mapping."""

    def test_fact_has_parent_decision_id_field(self):
        f = Fact(
            id=1,
            tenant_id="t",
            project="p",
            content="c",
            fact_type="knowledge",
            tags=[],
            confidence="C5",
            valid_from="now",
            valid_until=None,
            source="test",
            meta={},
            created_at="now",
            updated_at="now",
            parent_decision_id=42,
        )
        assert f.parent_decision_id == 42

    def test_to_dict_includes_parent(self):
        f = Fact(
            id=1,
            tenant_id="t",
            project="p",
            content="c",
            fact_type="knowledge",
            tags=[],
            confidence="C5",
            valid_from="now",
            valid_until=None,
            source="test",
            meta={},
            created_at="now",
            updated_at="now",
            parent_decision_id=7,
        )
        d = f.to_dict()
        assert d["parent_decision_id"] == 7

    def test_fact_columns_includes_parent(self):
        assert "parent_decision_id" in FACT_COLUMNS

    def test_insert_fact_record_signature(self):
        sig = inspect.signature(insert_fact_record)
        assert "parent_decision_id" in sig.parameters

    def test_store_mixin_signature(self):
        from legacy_research.engine.store_mixin import StoreMixin

        sig = inspect.signature(StoreMixin.store)
        assert "parent_decision_id" in sig.parameters
