# [C5-REAL] Exergy-Maximized
"""
Minimal Trusted Kernel (MTK) Core.
The ONLY authorized entry point for state mutation. Replaces 'distributed systems cosplay'
with a single, hard-enforced physical checkpoint.
"""

import hashlib
import time
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from cortex.types.evidence import ClosurePayload
from cortex.engine.mtk_sqlite_authorizer import mtk_active_token

class MTKGuard:
    """
    The Minimal Trusted Kernel (MTK) Boundary.
    Enforces atomic, synchronous-like deterministic evaluation of state mutations.
    """
    def __init__(self, private_key: str):
        self.private_key = private_key
        
    def _generate_ephemeral_token(self, payload: ClosurePayload) -> str:
        """Generate a short-lived cryptographic capability token for this transaction."""
        babylon_time = time.time_ns()
        raw = f"{payload.canonical()}:{babylon_time}:{self.private_key}"
        return f"mtk_auth_{hashlib.sha3_256(raw.encode()).hexdigest()}"

    @asynccontextmanager
    async def transaction_boundary(self, payload: ClosurePayload) -> AsyncGenerator[str, None]:
        """
        The absolute physical chokepoint.
        1. Verify the payload's taint/evidence chain.
        2. Mint the ephemeral MTK token.
        3. Open the ContextVar so SQLite authorizer permits the write.
        4. Yield control for the DB write.
        5. Destroy the token.
        """
        # Step 1: Verify Payload Integrity
        if not payload.evidence or not payload.claims:
            raise ValueError("MTK-REJECT: Missing evidence or claims in payload.")
            
        if not payload.verdict:
            raise ValueError("MTK-REJECT: Payload verdict is negative. Causality broken.")
            
        # Step 2: Mint Ephemeral Token
        token = self._generate_ephemeral_token(payload)
        
        # Step 3: Open Physical DB Boundary
        token_id = mtk_active_token.set(token)
        
        try:
            # Yield to the execution layer
            # Any DB operation here will be authorized by SQLite engine
            yield token
        finally:
            # Step 5: Destroy the physical capability
            mtk_active_token.reset(token_id)
