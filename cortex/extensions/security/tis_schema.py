"""Transaction Intent Schema (TIS) — CORTEX Implementation.

Aligned with arXiv:2601.04583v1 §8.2 Transaction Intent Schema.
Provides portable, unambiguous intent specification for agent–chain
interactions in the Ouroboros strike pipeline.

This module defines the TIS dataclass and validation logic. Every
strike ledger entry SHOULD carry TIS-aligned fields to enable
PDR-compatible audit trails.

Reference: Appendix A — TIS Reference Implementation (JSON Schema Draft-07).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class TransactionIntentSchema:
    """TIS Core Schema — portable on-chain intent specification.

    Attributes:
        intent_id: Unique identifier for this intent (UUID4).
        chain_id: Target chain (1=ETH, 10=OP, 8453=Base, etc.). None for off-chain.
        sender: Originating address or agent identifier.
        target_contract: Primary target contract address, if applicable.
        intent_type: "audit_strike" | "swap" | "transfer" | "governance" | "stake".
        operations: List of operation descriptors.
        constraints: Execution constraints (slippage, deadline, etc.).
        metadata: Agent-specific metadata including reasoning trace hash.
        created_at: ISO8601 creation timestamp.
    """

    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chain_id: Optional[int] = None
    sender: str = ""
    target_contract: str = ""
    intent_type: str = "audit_strike"
    operations: list[dict[str, Any]] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ─── Allowed intent types ─────────────────────────────────────
    VALID_INTENT_TYPES = frozenset({
        "audit_strike",     # Bounty strike submission
        "swap",             # Token swap
        "transfer",         # Value transfer
        "governance",       # Governance vote/delegation
        "stake",            # Staking/unstaking
        "bridge",           # Cross-chain bridge
        "deploy",           # Contract deployment
    })

    def validate(self) -> list[str]:
        """Validate TIS against schema constraints.

        Returns:
            List of validation errors. Empty list = valid.
        """
        errors: list[str] = []

        if not self.intent_id:
            errors.append("intent_id is required")

        if self.intent_type not in self.VALID_INTENT_TYPES:
            errors.append(
                f"invalid intent_type '{self.intent_type}'. "
                f"Allowed: {', '.join(sorted(self.VALID_INTENT_TYPES))}"
            )

        if self.chain_id is not None and self.chain_id < 0:
            errors.append(f"chain_id must be non-negative, got {self.chain_id}")

        return errors

    def canonical_hash(self) -> str:
        """Compute deterministic SHA-256 hash of canonical TIS representation.

        Uses JSON canonical form (sorted keys, no whitespace) per
        Appendix A.2 canonicalization spec.
        """
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Export TIS as dictionary for JSONL serialization."""
        return asdict(self)

    @classmethod
    def from_strike_entry(cls, entry: dict[str, Any]) -> "TransactionIntentSchema":
        """Construct TIS from existing Ouroboros strike ledger entry.

        Maps legacy fields to TIS-aligned schema:
        - vulnerability_id → metadata.vulnerability_id
        - target → metadata.target
        - taint → metadata.taint_hash
        - chain_id → chain_id (new field, defaults to None)
        - target_contract → target_contract (new field, defaults to "")
        """
        protocol = entry.get("protocol", "").lower()
        target_name = entry.get("target", "").lower()

        # Infer chain from known protocols
        chain_id = entry.get("chain_id")
        if chain_id is None:
            if "exactly" in protocol:
                chain_id = 10  # Optimism
            elif "firedancer" in target_name or "solana" in target_name:
                chain_id = None  # Solana = non-EVM
            elif "bitflow" in protocol or "stacks" in target_name:
                chain_id = None  # Stacks = non-EVM
            elif "folks" in protocol or "algorand" in target_name:
                chain_id = None  # Algorand = non-EVM
            elif "hats" in protocol or "insurace" in protocol:
                chain_id = 1  # Ethereum mainnet
            elif "k2" in protocol:
                chain_id = 1  # Ethereum mainnet
            elif "layerzero" in protocol:
                chain_id = None  # Multi-chain

        return cls(
            chain_id=chain_id,
            target_contract=entry.get("target_contract", ""),
            intent_type="audit_strike",
            metadata={
                "vulnerability_id": entry.get("vulnerability_id", ""),
                "target": entry.get("target", ""),
                "protocol": entry.get("protocol", ""),
                "severity": entry.get("severity", ""),
                "platform": entry.get("platform", ""),
                "taint_hash": entry.get("taint", ""),
            },
        )
