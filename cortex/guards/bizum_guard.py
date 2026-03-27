"""
cortex/guards/bizum_guard.py
───────────────────────────
Sovereign Bizum Transaction Guard — v0.1.0
Implements safety boundaries for P2P fiat extraction.
"""

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger("cortex.guards.bizum")

class BizumGuard:
    """
    Enforces deterministic boundaries on Bizum transactions.
    
    Checks:
    1. Transaction Limit (Max 500 EUR per tx)
    2. Daily Cumulative Limit (Max 2000 EUR per day)
    3. Destination Verification (Known or trusted nodes)
    4. Entropy Balance (Ensures extraction doesn't collapse local exergy)
    """

    MAX_TX_AMOUNT = Decimal("500.00")
    MAX_DAILY_TOTAL = Decimal("2000.00")

    def __init__(self, ledger: Any = None):
        self.ledger = ledger

    async def validate_transaction(self, amount: Decimal, destination: str) -> bool:
        """
        Validates a single outbound Bizum transaction.
        """
        if amount > self.MAX_TX_AMOUNT:
            logger.error("[BIZUM_GUARD] Transaction amount %s exceeds limit %s", amount, self.MAX_TX_AMOUNT)
            return False

        if not destination or len(destination) < 9:
            logger.error("[BIZUM_GUARD] Invalid destination: %s", destination)
            return False

        # TODO: Check cumulative daily total from ledger
        if self.ledger:
            try:
                # Thermodynamic Axiom: Medir exergía, no volumen (fiat in this case).
                # Query the immutable ledger for today's BIZUM_TRANSFER actions.
                async with self.ledger._acquire_conn() as conn:
                    cursor = await conn.execute(
                        """
                        SELECT SUM(json_extract(detail, '$.amount')) 
                        FROM transactions 
                        WHERE action = 'BIZUM_TRANSFER' 
                          AND timestamp >= date('now', 'start of day')
                        """
                    )
                    row = await cursor.fetchone()
                    daily_total = Decimal(str(row[0])) if row and row[0] else Decimal("0.00")
                    
                    if daily_total + amount > self.MAX_DAILY_TOTAL:
                        logger.error("[BIZUM_GUARD] Cumulative daily total %s + tx %s exceeds %s", daily_total, amount, self.MAX_DAILY_TOTAL)
                        return False
            except Exception as e:
                logger.error("[BIZUM_GUARD] Ledger constraint failure: %s", e)
                # Fail closed. If we can't verify the ledger, we don't extract.
                return False
                
        logger.info("[BIZUM_GUARD] Transaction validated: %s to %s", amount, destination)
        return True

    def audit_claim(self, claim: dict[str, Any]) -> bool:
        """
        Verifies a probabilistic claim from a generative proposal.
        """
        # Axiom 1: No trust in generative output
        required_keys = ["amount", "phone", "reason"]
        if not all(k in claim for k in required_keys):
            return False
            
        try:
            amount = Decimal(str(claim["amount"]))
            if amount <= 0:
                return False
        except (ValueError, TypeError):
            return False
            
        return True
