"""Fact Layer Models (CLI/SDK Ingestion)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

__all__ = ["IngestionFact", "Provenance"]


class Provenance(str, Enum):
    USER_DIRECT = "user_direct"
    INFERENCE = "inference"
    SYSTEM = "system"
    EXTERNAL = "external"


class IngestionFact(BaseModel):
    """V8 Guardrail: Strict input validation before processing."""

    project: str = Field(..., min_length=1)
    content: str = Field(..., min_length=10)
    tenant_id: str = Field(..., min_length=1)
    confidence: str = Field(..., pattern=r"^(C[1-5]|stated|inferred)$")
    source: Provenance = Field(
        default=Provenance.SYSTEM,
        description="Provenance / Data origin (Source Monitoring)"
    )
