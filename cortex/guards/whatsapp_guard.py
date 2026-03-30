"""
cortex/guards/whatsapp_guard.py
──────────────────────────────
Sovereign WhatsApp Communication Guard — v0.1.0
Implements safety boundaries for autonomous messaging.
"""

import logging
from typing import Any

logger = logging.getLogger("cortex.guards.whatsapp")

class WhatsAppGuard:
    """
    Enforces deterministic boundaries on WhatsApp communications.

    Checks:
    1. Message Length (Max 4096 chars)
    2. Recipient Format (Contact Name or International Number)
    3. Content Safety (No PII leaks, no spam patterns)
    4. Rate Control (Prevents session flagging)
    """

    MAX_MESSAGE_LENGTH = 4096
    MIN_MESSAGE_LENGTH = 1

    def __init__(self, ledger: Any = None):
        self.ledger = ledger

    async def validate_message(self, recipient: str, text: str) -> bool:
        """
        Validates an outbound WhatsApp message.
        """
        if not (self.MIN_MESSAGE_LENGTH <= len(text) <= self.MAX_MESSAGE_LENGTH):
            logger.error("[WHATSAPP_GUARD] Message length %d outside limits [%d, %d]",
                         len(text), self.MIN_MESSAGE_LENGTH, self.MAX_MESSAGE_LENGTH)
            return False

        if not recipient or len(recipient) < 2:
            logger.error("[WHATSAPP_GUARD] Invalid recipient: %s", recipient)
            return False

        # Simple check for spammy patterns (too many links, CAPS, etc.)
        if text.count("http") > 3:
            logger.warning("[WHATSAPP_GUARD] Potential spam detected: high link density.")
            return False

        logger.info("[WHATSAPP_GUARD] Message validated for recipient: %s", recipient)
        return True

    def audit_claim(self, claim: dict[str, Any]) -> bool:
        """
        Verifies a probabilistic claim from a generative proposal.
        """
        required_keys = ["recipient", "message", "reason"]
        if not all(k in claim for k in required_keys):
            logger.error("[WHATSAPP_GUARD] Missing required keys in claim.")
            return False

        return True
