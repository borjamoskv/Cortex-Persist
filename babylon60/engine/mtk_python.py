import hashlib
import time

# [C5-REAL] Exergy-Maximized
# MTK (Minimal Trusted Kernel) - Python Boundary (Compressed)
from babylon60.engine.mtk_sqlite_authorizer import mtk_active_token as mtk_ephemeral_token

_PRIVATE_KEY = "CORTEX_LOCAL_KEY_12345" # In production, read from ENV or Keyring

def mint_ephemeral_token(payload: str) -> str:
    now = str(time.time())
    raw = f"{payload}:{_PRIVATE_KEY}:{now}".encode()
    token = hashlib.sha256(raw).hexdigest()
    return f"mtk_auth_{token}"

def set_ephemeral_token(token: str) -> None:
    mtk_ephemeral_token.set(token)

def clear_ephemeral_token() -> None:
    mtk_ephemeral_token.set(None)
