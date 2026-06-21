# [C5-REAL] Exergy-Maximized
"""
Minimal Trusted Kernel (MTK) Core.
The ONLY authorized entry point for state mutation. Replaces 'distributed systems cosplay'
with a single, hard-enforced physical checkpoint.
"""

import hashlib
import time
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

try:
    import cortex_core_rs
except ImportError:
    cortex_core_rs = None

from cortex.engine.mtk_sqlite_authorizer import mtk_active_token
from cortex.types.evidence import ClosurePayload

logger = logging.getLogger(__name__)

class MTKGuard:
    """
    The Minimal Trusted Kernel (MTK) Boundary.
    Enforces atomic, synchronous-like deterministic evaluation of state mutations.
    """
    def __init__(self, private_key: str):
        self.private_key = private_key
        if cortex_core_rs:
            self.ast_projector = cortex_core_rs.ASTProjector()
            self.rust_authorizer = cortex_core_rs.MTKAuthorizer()
        else:
            self.ast_projector = None
            self.rust_authorizer = None
            
    def validate_c5_ast(self, source_code: str) -> str:
        """Invokes the Rust AST Projector to validate C5-REAL constraints."""
        if self.ast_projector:
            return self.ast_projector.ingest_c5_real(source_code)
        return ""
        
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
        # Step 1: Formal State Admission System (AX-XI)
        # Valid(n_i) = Parent(n_i) ∈ S_{i-1} ∧ Verify(n_i) ∧ Bounded(n_i)
        
        # 1.1 Invariante Causal (I_causal)
        if not payload.evidence or not payload.claims:
            raise ValueError("MTK-REJECT: Missing evidence or claims in payload. Causal continuity broken.")
        if not payload.verdict:
            raise ValueError("MTK-REJECT: Payload verdict is negative. Causal DAG evaluation failed.")
            
        # 1.2 Invariante Criptográfico (I_crypto)
        # TODO: Inject Ed25519 payload signature verification here.
        # if not verify_zk_seal(payload.payload_hash, payload.signature): raise ValueError(...)
        
        # 1.3 Invariante Termodinámico/Complejidad (I_complexity) (Ω₁₃)
        # The MTK physically rejects transactions whose Informational Exergy is too low (Anergy).
        # This acts as the Szilard Engine gate: no capability token is minted for pure entropy.
        if hasattr(payload, "info_exergy") and payload.info_exergy < 0.1:
            raise ValueError(f"MTK-REJECT: Informational Exergy too low ({payload.info_exergy} < 0.1). Entropy purge required before DB write.")
            
        # Step 2: Mint Ephemeral Token
        token = self._generate_ephemeral_token(payload)
        
        # Step 3: Open Physical DB Boundary
        token_id = mtk_active_token.set(token)
        if self.rust_authorizer:
            self.rust_authorizer.set_ephemeral_token(token)
        
        try:
            # Yield to the execution layer
            # Any DB operation here will be authorized by SQLite engine
            yield token
        finally:
            # Step 5: Destroy the physical capability
            if self.rust_authorizer:
                self.rust_authorizer.clear_token()
            mtk_active_token.reset(token_id)
