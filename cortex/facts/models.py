"""Fact Layer Models (CLI/SDK Ingestion)."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["IngestionFact"]


class IngestionFact(BaseModel):
    """V8 Guardrail: Strict input validation before processing."""

    project: str = Field(..., min_length=1)
    content: str = Field(..., min_length=10)
    tenant_id: str = Field(..., min_length=1)
    confidence: str = Field(..., pattern=r"^(C[1-5]|stated|inferred)$")
    # Mapping 'source' parameter to 'provenance' conceptually
    source: str = Field(..., min_length=1, description="Provenance / Data origin")
