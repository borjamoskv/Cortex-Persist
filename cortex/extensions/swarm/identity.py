import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)


class IdentityAnchor:
    """Sovereign Identity Anchor for ΩΩ-HANDOFF (Arweave Integration).
    
    Generates and manages RSA-PSS 4096-bit signatures matching the Arweave 
    cryptographic specification for L1 data anchoring.
    """

    def __init__(self, private_key: rsa.RSAPrivateKey):
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def generate(cls) -> "IdentityAnchor":
        """Generate a new 4096-bit RSA key suitable for Arweave."""
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )
        return cls(key)

    @classmethod
    def from_pem(cls, pem_bytes: bytes, password: bytes | None = None) -> "IdentityAnchor":
        """Load an identity from a PEM-encoded private key."""
        key = load_pem_private_key(pem_bytes, password=password)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("IdentityAnchor requires an RSA private key")
        return cls(key)

    def export_pem(self) -> bytes:
        """Export the private key in PEM format."""
        return self._private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )

    def export_public_jwk(self) -> dict[str, str]:
        """Export the public key in JWK format (used by Arweave)."""
        numbers = self._public_key.public_numbers()
        n_bytes = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, byteorder="big")
        e_bytes = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, byteorder="big")
        return {
            "kty": "RSA",
            "e": base64.urlsafe_b64encode(e_bytes).decode("ascii").rstrip("="),
            "n": base64.urlsafe_b64encode(n_bytes).decode("ascii").rstrip("="),
        }

    @property
    def address(self) -> str:
        """Arweave address is the Base64URL(SHA-256) of the public key `n`."""
        jwk = self.export_public_jwk()
        n_bytes = base64.urlsafe_b64decode(jwk["n"] + "==")
        digest = hashlib.sha256(n_bytes).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def sign(self, payload: bytes) -> bytes:
        """Sign a payload using RSA-PSS SHA-256 (Arweave standard)."""
        signature = self._private_key.sign(
            payload,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=32, # Arweave uses 32-byte salts for PSS
            ),
            hashes.SHA256(),
        )
        return signature

    def verify(self, payload: bytes, signature: bytes) -> bool:
        """Verify an RSA-PSS signature."""
        try:
            self._public_key.verify(
                signature,
                payload,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=32,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False
