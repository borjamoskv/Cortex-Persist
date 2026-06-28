# [C5-REAL] Exergy-Maximized
"""RustChain Wallet Representation.

Matches the Ed25519-based RustChainWallet SDK interface.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class RustChainWallet:
    """Ed25519-based wallet matching the RustChain SDK wallet interface."""

    ADDRESS_PREFIX = "RTC"

    def __init__(self, private_key: ed25519.Ed25519PrivateKey) -> None:
        self._private_key = private_key
        self._public_key = private_key.public_key()

        # Address: prefix + first 20 bytes of double SHA256 of b"address" + public_key_bytes
        pub_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        h1 = hashlib.sha256(b"address" + pub_bytes).digest()
        h2 = hashlib.sha256(h1).digest()
        self._address = self.ADDRESS_PREFIX + h2[:20].hex()

    @classmethod
    def create(cls) -> RustChainWallet:
        """Create a new random keypair wallet."""
        priv = ed25519.Ed25519PrivateKey.generate()
        return cls(priv)

    @classmethod
    def from_private_key_bytes(cls, key_bytes: bytes) -> RustChainWallet:
        """Load wallet from raw private key bytes."""
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(key_bytes)
        return cls(priv)

    @property
    def address(self) -> str:
        return self._address

    @property
    def public_key_bytes(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

    @property
    def public_key_hex(self) -> str:
        return self.public_key_bytes.hex()

    def sign(self, message: bytes) -> bytes:
        """Sign raw message bytes."""
        return self._private_key.sign(message)

    def sign_transfer(self, to_address: str, amount: int, fee: int = 0) -> dict[str, Any]:
        """Sign a transfer payload."""
        timestamp = int(time.time())
        payload = f"{self._address}:{to_address}:{amount}:{fee}:{timestamp}".encode()
        signature = self.sign(payload)
        return {
            "from": self._address,
            "to": to_address,
            "amount": amount,
            "fee": fee,
            "timestamp": timestamp,
            "signature": signature.hex(),
        }
