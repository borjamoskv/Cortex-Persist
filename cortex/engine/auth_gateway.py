import logging
import time
from typing import Any
import json
import uuid

logger = logging.getLogger("cortex.engine.auth_gateway")

class AuthGateway:
    """
    Operator Override Integrity Gateway.
    Generates deterministic pending authorization requests in the CORTEX Ledger
    that require explicit C5-REAL cryptographic or manual CLI signature to proceed.
    """
    
    def __init__(self, engine: Any):
        self.engine = engine
        
    async def ensure_table(self) -> None:
        """Ensures the auth_requests table exists in the DB."""
        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                '''CREATE TABLE IF NOT EXISTS auth_requests (
                    id TEXT PRIMARY KEY,
                    hypothesis TEXT,
                    state_payload TEXT,
                    status TEXT,
                    created_at REAL,
                    resolved_at REAL,
                    signature TEXT,
                    public_key TEXT
                )'''
            )
            conn.commit()
            
            # Perform schema migration if needed (idempotent addition of new columns)
            try:
                conn.execute("ALTER TABLE auth_requests ADD COLUMN signature TEXT")
                conn.execute("ALTER TABLE auth_requests ADD COLUMN public_key TEXT")
                conn.commit()
            except Exception:
                pass # Columns likely already exist
        except Exception as e:
            logger.error("Failed to ensure auth_requests table: %s", e)
            
    async def request_override(self, hypothesis: str, state: dict[str, Any]) -> str:
        """
        Creates an authorization request for the Operator. 
        Returns the Request ID.
        """
        req_id = f"AUTH-{str(uuid.uuid4())[:8].upper()}"
        logger.info("[AuthGateway] Issuing Operator Override Request: %s", req_id)
        
        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                '''INSERT INTO auth_requests (id, hypothesis, state_payload, status, created_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (req_id, hypothesis, json.dumps(state), "PENDING", time.monotonic())
            )
            conn.commit()
            logger.warning("[AuthGateway] Action suspended. Awaiting Operator Approval for %s", req_id)
            logger.warning("To approve, run: cortex auth approve %s", req_id)
        except Exception as e:
            logger.error("[AuthGateway] DB insert failed: %s", e)
            
        return req_id
        
    async def approve_request(self, req_id: str, signature_b64: str, public_key_b64: str) -> bool:
        """Approves a request if and only if the Ed25519 signature over the payload is mathematically valid."""
        try:
            from cortex.extensions.security.signatures import Ed25519Signer, SignatureVerificationError
            
            conn = self.engine.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT status, state_payload FROM auth_requests WHERE id = ?", (req_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.error("[AuthGateway] Request %s not found.", req_id)
                return False
                
            status, state_payload = row
                
            if status != "PENDING":
                logger.warning("[AuthGateway] Request %s is already %s.", req_id, status)
                return False
                
            # C5-REAL Cryptographic Verification
            # We treat the req_id as the fact_hash and the state_payload as the content
            signer = Ed25519Signer(public_key_bytes=None) # We will verify using the provided pubkey
            
            try:
                signer.verify(content=state_payload, fact_hash=req_id, signature_b64=signature_b64, public_key_b64=public_key_b64)
                logger.info("[AuthGateway] Ed25519 Signature Verified for %s", req_id)
            except Exception as sig_err:
                logger.error("[AuthGateway] CRITICAL: Cryptographic Verification Failed for %s. Rejecting override.", req_id)
                # Fail open to rejection if signature is forged
                return False
                
            conn.execute(
                "UPDATE auth_requests SET status = 'APPROVED', resolved_at = ?, signature = ?, public_key = ? WHERE id = ?",
                (time.monotonic(), signature_b64, public_key_b64, req_id)
            )
            conn.commit()
            logger.info("[AuthGateway] Request %s APPROVED by Operator.", req_id)
            return True
        except Exception as e:
            logger.error("[AuthGateway] Failed to approve request %s: %s", req_id, e)
            return False
            
    async def reject_request(self, req_id: str) -> bool:
        """Rejects a request."""
        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                "UPDATE auth_requests SET status = 'REJECTED', resolved_at = ? WHERE id = ?",
                (time.monotonic(), req_id)
            )
            conn.commit()
            logger.info("[AuthGateway] Request %s REJECTED by Operator.", req_id)
            return True
        except Exception as e:
            logger.error("[AuthGateway] Failed to reject request %s: %s", req_id, e)
            return False
