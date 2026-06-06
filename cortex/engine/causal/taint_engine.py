# [C5-REAL] Exergy-Maximized
import base64
import hashlib
import json
import logging
import time
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

logger = logging.getLogger("cortex.engine.causal.taint_engine")


class TaintValidationError(ValueError):
    """Raised when a proposal lacks a valid CORTEX-TAINT token or fails cryptographic verification."""

    pass


def canonicalize_content(content: str) -> str:
    """Normalizes content string to ensure consistent hashing."""
    normalized = "\n".join(line.strip() for line in content.strip().splitlines())
    try:
        data = json.loads(normalized)
        if isinstance(data, (dict, list)):
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
    except Exception as exc:
        logger.warning("Suppressed exception: %s", exc)
    return normalized


def generate_secure_taint_token(
    agent_id: str, session_id: str, content: str, private_key_b64: str, nonce: str | None = None
) -> str:
    """Generates a secure cryptographically signed CORTEX-TAINT token.

    Format: taint:{agent_id}:{session_id}:{timestamp_iso8601}:{nonce}:{signature}
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    if not nonce:
        import uuid

        nonce = uuid.uuid4().hex

    canonical_content = canonicalize_content(content)
    content_hash = hashlib.sha3_256(canonical_content.encode("utf-8")).hexdigest()

    canonical_payload = f"agent_id={agent_id}&session_id={session_id}&timestamp={timestamp}&nonce={nonce}&content_hash={content_hash}"

    priv_bytes = base64.b64decode(private_key_b64)
    priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    sig_bytes = priv_key.sign(canonical_payload.encode("utf-8"))
    signature = base64.b64encode(sig_bytes).decode("ascii")

    return f"taint:{agent_id}:{session_id}:{timestamp}:{nonce}:{signature}"


def parse_utc_timestamp(ts_str: str) -> datetime:
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _query_agent_key_sync(conn, agent_id: str) -> str | None:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT public_key FROM agents WHERE id = ? AND is_active = 1", (agent_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error("[TaintEngine] Failed to query agent key sync: %s", e)
        return None


async def _query_agent_key_async(conn, agent_id: str) -> str | None:
    try:
        cursor = await conn.execute(
            "SELECT public_key FROM agents WHERE id = ? AND is_active = 1", (agent_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error("[TaintEngine] Failed to query agent key async: %s", e)
        return None


def _check_and_register_nonce_sync(conn, nonce: str) -> bool:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS taint_nonces (
            nonce TEXT PRIMARY KEY,
            timestamp REAL
        )
    """)
    cursor = conn.cursor()
    cursor.execute("SELECT nonce FROM taint_nonces WHERE nonce = ?", (nonce,))
    if cursor.fetchone():
        return False
    conn.execute("INSERT INTO taint_nonces (nonce, timestamp) VALUES (?, ?)", (nonce, time.time()))
    conn.commit()
    return True


async def _check_and_register_nonce_async(conn, nonce: str) -> bool:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS taint_nonces (
            nonce TEXT PRIMARY KEY,
            timestamp REAL
        )
    """)
    cursor = await conn.execute("SELECT nonce FROM taint_nonces WHERE nonce = ?", (nonce,))
    if await cursor.fetchone():
        return False
    await conn.execute(
        "INSERT INTO taint_nonces (nonce, timestamp) VALUES (?, ?)", (nonce, time.time())
    )
    await conn.commit()
    return True


def _is_async_conn(conn) -> bool:
    return "aiosqlite" in type(conn).__module__


async def verify_taint_token(conn, token: str | None, content: str) -> bool:
    """Verifies a secure cryptographically signed CORTEX-TAINT token.

    Checks:
    1. Token format.
    2. Agent registration & public key validation.
    3. Expiration window (5 minutes).
    4. Replay attack prevention (nonce tracking).
    5. Ed25519 signature validity.
    """
    if not token:
        logger.error(
            "[TaintEngine] SAGA-1: Rejecting proposal due to missing CORTEX-TAINT signature."
        )
        return False

    parts = token.split(":")
    if len(parts) < 6:
        logger.error("[TaintEngine] SAGA-1: Invalid token structure: %s", token)
        return False

    prefix = parts[0]
    agent_id = parts[1]
    session_id = parts[2]
    # Timestamp, nonce, and signature
    signature = parts[-1]
    nonce = parts[-2]
    timestamp_str = ":".join(parts[3:-2])

    if prefix != "taint":
        logger.error("[TaintEngine] SAGA-1: Token prefix must be 'taint': %s", prefix)
        return False

    if not agent_id or not session_id or not nonce or not signature:
        logger.error("[TaintEngine] SAGA-1: Missing vital fields in taint token.")
        return False

    # 1. Verify Timestamp Expiration Window
    try:
        token_time = parse_utc_timestamp(timestamp_str)
        now = datetime.now(timezone.utc)
        diff = abs((now - token_time).total_seconds())
        if diff > 300:  # 5 minutes window
            logger.error("[TaintEngine] SAGA-1: Taint token has expired. Drift: %.1fs", diff)
            return False
    except ValueError:
        logger.error("[TaintEngine] SAGA-1: Invalid ISO-8601 timestamp in token: %s", timestamp_str)
        return False

    # 2. Check Replay Attack (Nonce ledger check)
    is_async = _is_async_conn(conn)
    if is_async:
        nonce_ok = await _check_and_register_nonce_async(conn, nonce)
    else:
        nonce_ok = _check_and_register_nonce_sync(conn, nonce)

    if not nonce_ok:
        logger.error("[TaintEngine] SAGA-1: Replay attack detected! Nonce already used: %s", nonce)
        return False

    # 3. Retrieve Agent Public Key
    if is_async:
        public_key_b64 = await _query_agent_key_async(conn, agent_id)
    else:
        public_key_b64 = _query_agent_key_sync(conn, agent_id)

    if not public_key_b64:
        logger.error("[TaintEngine] SAGA-1: Agent %s is not registered or inactive.", agent_id)
        return False

    # 4. Verify Signature
    canonical_content = canonicalize_content(content)
    content_hash = hashlib.sha3_256(canonical_content.encode("utf-8")).hexdigest()
    canonical_payload = f"agent_id={agent_id}&session_id={session_id}&timestamp={timestamp_str}&nonce={nonce}&content_hash={content_hash}"

    try:
        pub_bytes = base64.b64decode(public_key_b64)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        sig_bytes = base64.b64decode(signature)
        pub_key.verify(sig_bytes, canonical_payload.encode("utf-8"))
        logger.info("[TaintEngine] Cryptographic Taint Signature verified for Agent %s", agent_id)
        return True
    except Exception as sig_err:
        logger.error(
            "[TaintEngine] SAGA-1: Cryptographic signature verification failed: %s", sig_err
        )
        return False


async def enforce_taint_check(conn, token: str | None, content: str) -> None:
    """Enforces the CORTEX-TAINT check. Raises TaintValidationError if invalid."""
    import os

    if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
        return

    # We await the verify_taint_token check
    is_valid = await verify_taint_token(conn, token, content)
    if not is_valid:
        raise TaintValidationError(
            "SAGA-1 Rejection: Valid cryptographically signed CORTEX-TAINT token is required."
        )
