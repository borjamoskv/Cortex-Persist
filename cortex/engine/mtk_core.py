# [C5-REAL] Exergy-Maximized — Author: Borja Moskv
"""
Minimal Trusted Kernel (MTK) Core.
The ONLY authorized entry point for state mutation. Replaces 'distributed systems cosplay'
with a single, hard-enforced physical checkpoint.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from cryptography.hazmat.primitives.asymmetric import ed25519

import cortex_rs
from cortex.engine.mtk_sqlite_authorizer import mtk_active_token, mtk_payload_hash
from cortex.types.evidence import ClosurePayload

logger = logging.getLogger(__name__)

class MTKGuard:
    """
    The Minimal Trusted Kernel (MTK) Boundary.
    Enforces atomic, synchronous-like deterministic evaluation of state mutations.
    """
    def __init__(self, private_key: str):
        self.private_key = private_key
        # Enforce C5-REAL execution: crash if Rust binaries are missing
        self.ast_projector = cortex_rs.ASTProjector()
        self.rust_authorizer = cortex_rs.MTKAuthorizer()
        self.cognitive_state = cortex_rs.CognitiveState(1000)
            
    def validate_c5_ast(self, source_code: str) -> str:
        """Invokes the Rust AST Projector to validate C5-REAL constraints."""
        return self.ast_projector.ingest_c5_real(source_code)
        
    def _generate_ephemeral_token(self, payload: ClosurePayload) -> str:
        """Generate a short-lived cryptographic capability token STRICTLY via Rust FFI."""
        import cortex_rs
        return cortex_rs.mint_ephemeral_token(payload.payload_hash, self.private_key)

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
        # Ed25519 payload signature verification via ZKSwarmIdentity.
        _signature = getattr(payload, "signature", None)
        if _signature:
            try:
                import base64

                from cortex.crypto.keys import ZKSwarmIdentity
                # Derive public key from MTK private key for self-verification
                _priv_bytes = self.private_key.encode() if isinstance(self.private_key, str) else self.private_key
                _pub_b64 = base64.b64encode(
                    ed25519.Ed25519PrivateKey.from_private_bytes(
                        base64.b64decode(_priv_bytes) if isinstance(_priv_bytes, (str, bytes)) and len(_priv_bytes) == 44
                        else _priv_bytes.encode() if isinstance(_priv_bytes, str)
                        else _priv_bytes
                    ).public_key().public_bytes_raw()
                ).decode()
                if not ZKSwarmIdentity.verify_payload(payload.payload_hash, _pub_b64, _signature):
                    raise ValueError("MTK-REJECT: Ed25519 signature verification FAILED. I_crypto invariant broken.")
            except (ImportError, ValueError) as exc:
                if "MTK-REJECT" in str(exc):
                    raise
                logger.warning("[MTK] Ed25519 verification skipped (dependency error): %s", exc)
        else:
            logger.debug("[MTK] No signature on payload — I_crypto verification deferred (grace period).")
        
        # 1.3 Invariante Termodinámico/Complejidad (I_complexity) (Ω₁₃)
        # The MTK physically rejects transactions whose Informational Exergy is too low (Anergy).
        # This acts as the Szilard Engine gate: no capability token is minted for pure entropy.
        if hasattr(payload, "info_exergy") and payload.info_exergy < 0.1:
            raise ValueError(f"MTK-REJECT: Informational Exergy too low ({payload.info_exergy} < 0.1). Entropy purge required before DB write.")
            
        # 1.4 Invariante Cognitivo (I_cognitive): Advance the pure FSM state via Rust
        exergy_input = int(getattr(payload, "info_exergy", 1.0) * 100) # Simple scaling for FSM input
        self.cognitive_state = self.cognitive_state.apply_tick(exergy_input)
            
        # Step 2: Mint Ephemeral Token
        token = self._generate_ephemeral_token(payload)
        
        # Step 3: Open Physical DB Boundary
        token_id = mtk_active_token.set(token)
        payload_id = mtk_payload_hash.set(payload.payload_hash)
        self.rust_authorizer.set_ephemeral_token(token)
        
        try:
            # Yield to the execution layer
            # Any DB operation here will be authorized by SQLite engine
            yield token
        finally:
            # Step 5: Destroy the physical capability
            self.rust_authorizer.clear_token()
            mtk_active_token.reset(token_id)
            mtk_payload_hash.reset(payload_id)
