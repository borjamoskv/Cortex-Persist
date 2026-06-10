"""
Deterministic patching module for C5-REAL tests.
Patches common sources of entropy (time, random, uuid, secrets) to ensure
that tests are fully deterministic and repeatable.
"""

import datetime
import os
import random
import secrets
import sys
import uuid

_GLOBAL_SEED = int(os.environ.get("CORTEX_C5_REAL_SEED", "42"))

def patch_random() -> None:
    """Fix random seeds and mock functions for strict C5-REAL determinism."""
    random.seed(_GLOBAL_SEED)
    random.random = lambda: 0.5
    random.randint = lambda a, b: 5

def patch_uuid() -> None:
    """Patch uuid4 to be deterministic."""
    def _mock_uuid4() -> uuid.UUID:
        return uuid.UUID("00000000-0000-4000-8000-000000000000")
        
    uuid.uuid4 = _mock_uuid4

def patch_secrets() -> None:
    """Patch secrets module to use deterministic PRNG."""
    _rng = random.Random(_GLOBAL_SEED + 1)
    
    secrets.choice = _rng.choice
    secrets.randbelow = _rng.randrange
    secrets.randbits = _rng.getrandbits
    
    def _mock_token_bytes(nbytes: int = 32) -> bytes:
        if hasattr(_rng, 'randbytes'):
            return _rng.randbytes(nbytes)
        return bytes(_rng.getrandbits(8) for _ in range(nbytes))
        
    secrets.token_bytes = _mock_token_bytes
    
    def _mock_token_hex(nbytes: int = 32) -> str:
        return _mock_token_bytes(nbytes).hex()
        
    secrets.token_hex = _mock_token_hex
    
    def _mock_token_urlsafe(nbytes: int = 32) -> str:
        import base64
        return base64.urlsafe_b64encode(_mock_token_bytes(nbytes)).rstrip(b'=').decode('ascii')
        
    secrets.token_urlsafe = _mock_token_urlsafe

def patch_time() -> None:
    """Patch datetime.datetime to return a deterministic value for now()."""
    class DeterministicDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            base_dt = datetime.datetime(2026, 6, 6, 0, 0, 0, tzinfo=datetime.timezone.utc)
            if tz:
                return base_dt.astimezone(tz)
            return base_dt
            
    sys.modules['datetime'].datetime = DeterministicDatetime

def apply_deterministic_patches() -> None:
    """Apply all deterministic patches."""
    patch_random()
    patch_uuid()
    patch_secrets()
    patch_time()
