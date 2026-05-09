import re
import hashlib
from cortex.utils.canonical import now_iso


def generate_cortex_taint(agent_id: str, session_id: str, payload: str) -> str:
    """Generate a valid CORTEX-TAINT signature for a payload.
    Format: taint:{agent_id}:{session_id}:{timestamp_iso8601}:{sha3_256_of_payload}
    """
    ts = now_iso()
    # sha3_256
    hash_obj = hashlib.sha3_256(payload.encode("utf-8")).hexdigest()
    return f"taint:{agent_id}:{session_id}:{ts}:{hash_obj}"


def validate_cortex_taint(taint: str, payload: str | None = None) -> bool:
    """Validate that a string conforms to the CORTEX-TAINT signature format.
    Optionally, verify the sha3-256 hash matches the payload if payload is provided.
    """
    if not taint or not taint.startswith("taint:"):
        return False

    # Splitting from right to left or just manually splitting properly,
    # since ISO timestamps contain colons (e.g. 2024-05-09T07:39:38.826+00:00).
    # Expected format: taint : {agent} : {session} : {ts} : {hash}
    # hash length is 64 hex characters. Let's just rsplit for the hash.

    parts = taint.rsplit(":", 1)
    # length will always be 2 because we checked startswith('taint:') above

    prefix_and_ts, hash_digest = parts
    if len(hash_digest) != 64:
        return False

    try:
        int(hash_digest, 16)
    except ValueError:
        return False

    prefix_parts = prefix_and_ts.split(":", 3)
    if len(prefix_parts) != 4:
        return False

    _, agent_id, session_id, ts = prefix_parts

    if not agent_id or not session_id or not ts:
        return False

    if payload is not None:
        expected_hash = hashlib.sha3_256(payload.encode("utf-8")).hexdigest()
        if expected_hash != hash_digest:
            return False

    return True
