# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""Tests for cortex.llm.boundary — Sovereign Immune Boundary O(1)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel, Field

from cortex.llm.boundary import ImmuneBoundary, _clean_llm_json

# ── Test Schemas ────────────────────────────────────────────────


class SimpleDecision(BaseModel):
    action: str
    confidence: float = Field(ge=0.0, le=1.0)


class CognitionSchema(BaseModel):
    """System 2 Schema — Paradoja Keter resolved."""

    internal_monologue: str
    decision: str


# ── Unit Tests ──────────────────────────────────────────────────


class TestCleanLlmJson:
    """Tests for _clean_llm_json helper."""

    def test_plain_json(self) -> None:
        assert _clean_llm_json('{"a": 1}') == '{"a": 1}'

    def test_markdown_json_block(self) -> None:
        raw = '```json\n{"a": 1}\n```'
        assert _clean_llm_json(raw) == '{"a": 1}'

    def test_markdown_generic_block(self) -> None:
        raw = '```\n{"a": 1}\n```'
        assert _clean_llm_json(raw) == '{"a": 1}'

    def test_whitespace_padding(self) -> None:
        raw = '  \n  {"a": 1}  \n  '
        assert _clean_llm_json(raw) == '{"a": 1}'


class TestImmuneBoundaryEnforce:
    """Tests for ImmuneBoundary.enforce() — O(1) Chemical Immunity."""

    def test_valid_json_passes(self) -> None:
        """A structurally valid JSON must pass O(1) without retries."""

        async def _gen(dfa_schema: dict[str, Any]) -> str:
            # Verify the DFA schema is passed (Axiom 14)
            assert "properties" in dfa_schema
            assert "action" in dfa_schema["properties"]
            return '{"action": "deploy", "confidence": 0.95}'

        result = asyncio.run(
            ImmuneBoundary.enforce(
                schema=SimpleDecision,
                generation_func=_gen,
            )
        )
        assert result.action == "deploy"
        assert result.confidence == 0.95

    def test_invalid_json_raises_cortex_error(self) -> None:
        """A structurally invalid JSON must raise CortexError immediately (no retries)."""
        from cortex.utils.errors import CortexError

        async def _gen(dfa_schema: dict[str, Any]) -> str:
            return "NOT A JSON AT ALL"

        with pytest.raises(CortexError, match="inmunidad química"):
            asyncio.run(
                ImmuneBoundary.enforce(
                    schema=SimpleDecision,
                    generation_func=_gen,
                )
            )

    def test_schema_violation_raises_cortex_error(self) -> None:
        """A valid JSON that violates Pydantic constraints must raise CortexError."""
        from cortex.utils.errors import CortexError

        async def _gen(dfa_schema: dict[str, Any]) -> str:
            # confidence > 1.0 violates Field(le=1.0)
            return '{"action": "deploy", "confidence": 99.9}'

        with pytest.raises(CortexError):
            asyncio.run(
                ImmuneBoundary.enforce(
                    schema=SimpleDecision,
                    generation_func=_gen,
                )
            )

    def test_dfa_schema_contains_required_fields(self) -> None:
        """The DFA schema passed to generation_func must contain model metadata."""
        captured_schema: dict[str, Any] = {}

        async def _gen(dfa_schema: dict[str, Any]) -> str:
            captured_schema.update(dfa_schema)
            return '{"action": "test", "confidence": 0.5}'

        asyncio.run(
            ImmuneBoundary.enforce(
                schema=SimpleDecision,
                generation_func=_gen,
            )
        )
        assert "properties" in captured_schema
        assert "action" in captured_schema["properties"]
        assert "confidence" in captured_schema["properties"]

    def test_system2_cognition_schema(self) -> None:
        """System 2 schema with internal_monologue must work with O(1) enforcement."""

        async def _gen(dfa_schema: dict[str, Any]) -> str:
            assert "internal_monologue" in dfa_schema["properties"]
            return '{"internal_monologue": "Analyzing causal chain...", "decision": "proceed"}'

        result = asyncio.run(
            ImmuneBoundary.enforce(
                schema=CognitionSchema,
                generation_func=_gen,
            )
        )
        assert "causal" in result.internal_monologue.lower()
        assert result.decision == "proceed"

    def test_markdown_wrapped_json_passes(self) -> None:
        """JSON wrapped in markdown code blocks must be cleaned and validated."""

        async def _gen(dfa_schema: dict[str, Any]) -> str:
            return '```json\n{"action": "analyze", "confidence": 0.8}\n```'

        result = asyncio.run(
            ImmuneBoundary.enforce(
                schema=SimpleDecision,
                generation_func=_gen,
            )
        )
        assert result.action == "analyze"
        assert result.confidence == 0.8
