"""
Key Registry for CORTEX-Persist Strict Origin Verification.
"""

from dataclasses import dataclass



@dataclass
class Key:
    """Represents a public key tied to an origin identifier."""

    key_id: str
    public_key_b64: str
    owner: str
    is_active: bool = True


class KeyRegistry:
    """Registry for managing authorized public keys."""

    def __init__(self):
        self._keys: dict[str, Key] = {}

    def register(self, key_id: str, public_key_b64: str, owner: str) -> Key:
        """Registers a new public key in the registry."""
        key = Key(key_id=key_id, public_key_b64=public_key_b64, owner=owner)
        self._keys[key_id] = key
        return key

    def get_key(self, key_id: str) -> Key | None:
        """Retrieves a public key by its ID."""
        return self._keys.get(key_id)

    def revoke(self, key_id: str) -> None:
        """Revokes an existing key, rendering it inactive."""
        if key_id in self._keys:
            self._keys[key_id].is_active = False
