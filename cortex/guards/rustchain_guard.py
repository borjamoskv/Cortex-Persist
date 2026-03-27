"""
cortex/guards/rustchain_guard.py
───────────────────────────────
Sovereign Rustchain Guard — v0.1.0
Implements the trust boundary between Python (CORTEX) and Rust (rustchain-mcp).
"""

import logging
from typing import Any

logger = logging.getLogger("cortex.guards.rustchain")


class RustchainGuard:
    """
    Enforces deterministic boundaries on Rustchain-MCP invocations.
    Checks:
    1. Wallet address format.
    2. Thermodynamic exergy required for chain interaction.
    3. Prevents bare/empty structural execution.
    """

    FRONTERA_LIMIT = 100  # CORTEX YOLO x10 Limit

    def __init__(self, ledger: Any = None):
        self.ledger = ledger
        self.current_frontera_usage = 0

    async def validate_transaction(
        self, wallet_address: str, chain_id: str, exergy_cost: int = 1
    ) -> bool:
        """
        Validates boundaries before invoking the Rustchain MCP tools.
        """
        if self.current_frontera_usage + exergy_cost > self.FRONTERA_LIMIT:
            logger.error(
                "[RUSTCHAIN_GUARD] Frontera +10 Exergy limit exceeded (Usage: %s + Cost: %s > %s).",
                self.current_frontera_usage,
                exergy_cost,
                self.FRONTERA_LIMIT,
            )
            return False

        if not wallet_address or not wallet_address.startswith("0x") or len(wallet_address) != 42:
            logger.error("[RUSTCHAIN_GUARD] Invalid EVM wallet address: %s", wallet_address)
            return False

        if not chain_id:
            logger.error("[RUSTCHAIN_GUARD] Missing chain_id.")
            return False

        logger.info(
            "[RUSTCHAIN_GUARD] Rustchain boundary check passed for %s on %s",
            wallet_address,
            chain_id,
        )
        return True

    def audit_claim(self, claim: dict[str, Any]) -> bool:
        """
        Verifies a probabilistic generation from a tool calling model
        before passing it to the Rust execution layer.
        """
        # Axiom 1: No trust in generative output
        required_keys = ["wallet_address", "chain_id", "operation"]
        if not all(k in claim for k in required_keys):
            logger.warning("[RUSTCHAIN_GUARD] Structural parsing rejected claim: missing keys.")
            return False

        operation = claim.get("operation")
        if operation not in ["sign", "transfer", "read_contract"]:
            logger.warning("[RUSTCHAIN_GUARD] Prohibited operation attempted: %s", operation)
            return False

        return True
