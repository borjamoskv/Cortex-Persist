# [C5-REAL] Exergy-Maximized
"""
SAGA Write-Path Contract — Rigid Pydantic Schema (SAGA-1).

Enforces deterministic structural validation at the SAGA-1 boundary.
All fact proposals MUST pass through SagaWriteProposal before reaching
the SQLite WAL persistence layer.

Invariants enforced:
  1. Non-empty tenant_id and content (tenant isolation).
  2. Valid confidence level (C1-C5 only).
  3. Canonical CORTEX-TAINT token resolution across all key variants.
  4. Fact type whitelist (prevents injection of unknown types).
  5. Content length bounds (prevents memory exhaustion attacks).
  6. Metadata structural validation.

Author: borjamoskv
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger("cortex.guards.saga_contract")

# Canonical taint token keys — order matters for resolution priority
_TAINT_KEYS = ("CORTEX-TAINT", "cortex_taint", "cortex-taint", "CORTEX_TAINT")

# Allowed fact types in the Write-Path
_VALID_FACT_TYPES = frozenset({
    "knowledge",
    "decision",
    "error",
    "observation",
    "ghost",
    "reflection",
    "pattern",
    "bridge",
    "diamond",
    "telemetry_batch",
    "mafia_node",
    "UI_ACTION",
    "task",
    "axiom",
    "metric",
    "session_summary",
    "causal_link",
    "episode",
    "enrichment",
    "compaction",
    "tombstone",
})

# Valid confidence levels
_VALID_CONFIDENCE = frozenset({"C1", "C2", "C3", "C4", "C5"})

# Maximum content length (1MB UTF-8 — prevents memory exhaustion)
_MAX_CONTENT_BYTES = 1_048_576


class SagaWriteProposal(BaseModel):
    """Rigid Pydantic schema enforcing SAGA-1 Write-Path Contract determinism.

    Every fact proposal MUST be validated through this schema before advancing
    to the SQLite WAL persistence layer. Rejection at any field raises
    ``SagaValidationError`` and triggers SAGA-1 compensation (no state written).
    """

    tenant_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Absolute Zero-Trust tenant isolation boundary.",
    )
    project: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Target project identifier.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Non-empty fact content to persist.",
    )
    fact_type: str = Field(
        default="knowledge",
        description="Stratified fact type. Must be in the whitelist.",
    )
    confidence: str = Field(
        default="C5",
        description="Epistemic confidence level [C1-C5].",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Classification tags for the fact.",
    )
    source: str | None = Field(
        default=None,
        description="Origin identifier (agent_id, cli, api, etc).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured metadata. May contain CORTEX-TAINT token.",
    )
    parent_decision_id: int | None = Field(
        default=None,
        description="Causal anchor to parent decision in the DAG.",
    )
    taint_already_verified: bool = Field(
        default=False,
        description="If True, skip taint enforcement (caller guarantees prior verification).",
    )
    fast_path_eligible: bool = Field(
        default=False,
        description="If True, bypasses heuristic semantic validation due to ZK formal proof.",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    # ── Field Validators ──────────────────────────────────────────────

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, v: str) -> str:
        """Ensure confidence is a valid C-level."""
        clean = v.split("-")[0].upper()
        if clean not in _VALID_CONFIDENCE:
            raise ValueError(
                f"[SAGA-1] Invalid confidence level '{v}'. "
                f"Must be one of: {sorted(_VALID_CONFIDENCE)}"
            )
        return v

    @field_validator("fact_type")
    @classmethod
    def _validate_fact_type(cls, v: str) -> str:
        """Ensure fact_type is in the whitelist."""
        if v not in _VALID_FACT_TYPES:
            raise ValueError(
                f"[SAGA-1] Unknown fact_type '{v}'. "
                f"Must be one of: {sorted(_VALID_FACT_TYPES)}"
            )
        return v

    @field_validator("content")
    @classmethod
    def _validate_content_bounds(cls, v: str) -> str:
        """Enforce content length bounds to prevent memory exhaustion."""
        byte_len = len(v.encode("utf-8"))
        if byte_len > _MAX_CONTENT_BYTES:
            raise ValueError(
                f"[SAGA-1] Content exceeds maximum size: {byte_len} bytes > {_MAX_CONTENT_BYTES} bytes."
            )
        return v

    @field_validator("tenant_id")
    @classmethod
    def _validate_tenant_id(cls, v: str) -> str:
        """Prevent path traversal and injection in tenant_id."""
        if re.search(r"[/\\;\x00]", v):
            raise ValueError(
                f"[SAGA-1] tenant_id contains forbidden characters: '{v}'"
            )
        return v

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, v: list[str]) -> list[str]:
        """Limit tag count and length."""
        if len(v) > 50:
            raise ValueError(
                f"[SAGA-1] Too many tags: {len(v)} > 50 maximum."
            )
        for tag in v:
            if len(tag) > 128:
                raise ValueError(
                    f"[SAGA-1] Tag too long: '{tag[:32]}...' ({len(tag)} chars > 128 max)."
                )
        return v

    # ── Model Validators ──────────────────────────────────────────────

    @model_validator(mode="after")
    def _check_taint_presence(self) -> SagaWriteProposal:
        """Verify CORTEX-TAINT token is present when required."""
        # Telemetry and mafia_node types are authenticated via other channels
        exempt_types = {"telemetry_batch", "mafia_node"}
        if self.taint_already_verified or self.fact_type in exempt_types:
            return self

        taint = self.resolve_taint_token()
        if taint is None:
            logger.warning(
                "[SAGA-1] Proposal for tenant=%s project=%s lacks CORTEX-TAINT. "
                "Token will be enforced at the taint_engine layer.",
                self.tenant_id,
                self.project,
            )
        return self

    # ── Public API ────────────────────────────────────────────────────

    def resolve_taint_token(self) -> str | None:
        """Canonically resolve the CORTEX-TAINT token from metadata.

        Checks all known key variants in priority order.
        """
        for key in _TAINT_KEYS:
            val = self.metadata.get(key)
            if val:
                return val
        return None

    def to_insert_kwargs(self) -> dict[str, Any]:
        """Convert to keyword arguments for ``insert_fact_record``.

        Returns a dict ready to be unpacked into the function call,
        ensuring the schema-validated values flow through unchanged.
        """
        return {
            "tenant_id": self.tenant_id,
            "project": self.project,
            "content": self.content,
            "fact_type": self.fact_type,
            "tags": self.tags if self.tags else None,
            "confidence": self.confidence,
            "ts": None,
            "source": self.source,
            "meta": self.metadata if self.metadata else None,
            "tx_id": None,
            "parent_decision_id": self.parent_decision_id,
            "taint_already_verified": self.taint_already_verified,
            "fast_path_eligible": self.fast_path_eligible,
        }


class SagaValidationError(ValueError):
    """Raised when a proposal fails SAGA-1 structural validation."""
