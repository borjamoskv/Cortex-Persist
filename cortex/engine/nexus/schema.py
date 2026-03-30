"""
CORTEX Nexus: Multi-tenant Schema Definition
RFC-047 / Project LEVIATHAN
"""

from typing import Optional
from pydantic import BaseModel, Field


class TenantRegistry(BaseModel):
    """Registry for autonomous agents ascribing to the Trust Substrate."""
    tenant_id: str = Field(..., description="Unique ID for the AI agent or startup")
    organization: str
    api_key_hash: str
    is_active: bool = True
    balance_usd: float = 0.0


class AuditLogEntry(BaseModel):
    """Structure for a single audit commit in the multi-tenant ledger."""
    tenant_id: str
    action_type: str = Field(..., description="e.g., llm_inference, tool_use, fact_persist")
    payload_hash: str
    causal_parent: Optional[str] = None
    timestamp: str
    merkle_root: str
