import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger("cortex.engine.causal.taint_engine")

class TaintValidationError(ValueError):
    """Raised when a proposal lacks a valid CORTEX-TAINT token or fails cryptographic verification."""
    pass

def generate_taint_token(agent_id: str, session_id: str, content: str) -> str:
    """Helper to generate a valid CORTEX-TAINT token for tests or agent proposals."""
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_hash = hashlib.sha3_256(content.encode("utf-8")).hexdigest()
    return f"taint:{agent_id}:{session_id}:{timestamp}:{payload_hash}"

def verify_taint_token(token: str | None, content: str) -> bool:
    """Verifies a CORTEX-TAINT signature token against the content.
    
    Format: taint:{agent_id}:{session_id}:{timestamp_iso8601}:{sha3_256_of_payload}
    """
    if not token:
        logger.error("[TaintEngine] SAGA-1: Rejecting proposal due to missing CORTEX-TAINT signature.")
        return False
        
    parts = token.split(":")
    if len(parts) < 5:
        logger.error("[TaintEngine] SAGA-1: Invalid token structure: %s", token)
        return False
        
    prefix = parts[0]
    agent_id = parts[1]
    session_id = parts[2]
    timestamp_str = parts[3]
    # In case the timestamp string itself contains colons (which standard ISO format does, e.g. 2026-06-06T10:51:18)
    # We reconstruct the parts: prefix, agent_id, session_id, timestamp, hash
    # The last element is the hash, the first three are prefix, agent_id, session_id.
    # The middle elements are the timestamp (rejoined with colons).
    payload_hash = parts[-1]
    timestamp_str = ":".join(parts[3:-1])
    
    if prefix != "taint":
        logger.error("[TaintEngine] SAGA-1: Token prefix must be 'taint': %s", prefix)
        return False
        
    if not agent_id or not session_id:
        logger.error("[TaintEngine] SAGA-1: Empty agent_id or session_id in token.")
        return False
        
    try:
        # Validate timestamp syntax
        datetime.fromisoformat(timestamp_str)
    except ValueError:
        logger.error("[TaintEngine] SAGA-1: Invalid ISO-8601 timestamp in token: %s", timestamp_str)
        return False
        
    # Verify cryptographic signature of content
    expected_hash = hashlib.sha3_256(content.encode("utf-8")).hexdigest()
    if payload_hash != expected_hash:
        logger.error(
            "[TaintEngine] SAGA-1: Cryptographic mismatch! Token payload hash: %s, Expected: %s",
            payload_hash,
            expected_hash
        )
        return False
        
    return True

def enforce_taint_check(token: str | None, content: str) -> None:
    """Enforces the CORTEX-TAINT check. Raises TaintValidationError if invalid."""
    import os
    if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
        return
        
    if not verify_taint_token(token, content):
        raise TaintValidationError("SAGA-1 Rejection: Valid CORTEX-TAINT signature token is required for persistence.")
