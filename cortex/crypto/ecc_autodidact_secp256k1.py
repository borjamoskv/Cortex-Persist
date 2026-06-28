"""
[C5-REAL] SOBERANÍA MATEMÁTICA: ELLIPTIC CURVE CRYPTOGRAPHY (secp256k1)
Implementación determinista y estructural para CORTEX-Persist.
Erradicación de "Black Boxes" criptográficas.

El grupo secp256k1 se define como:
y^2 = x^3 + 7 (mod p)

Author: borjamoskv (SYS_ID: borjamoskv)
"""

import base64
import hashlib
import os
from typing import NamedTuple, Optional

# --- PARÁMETROS DEL DOMINIO secp256k1 ---
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
A = 0
B = 7
G_X = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
G_Y = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (G_X, G_Y)

def _inv_mod(k: int, p: int) -> int:
    """Inverso multiplicativo modular vía el Teorema Pequeño de Fermat: k^(p-2) mod p"""
    if k == 0:
        raise ZeroDivisionError('Division by zero in finite field.')
    return pow(k, p - 2, p)

def _point_add(p1: Optional[tuple[int, int]], p2: Optional[tuple[int, int]]) -> Optional[tuple[int, int]]:
    """Suma de puntos P1 + P2 en la curva elíptica secp256k1."""
    if p1 is None: return p2
    if p2 is None: return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 != y2:
        return None  # Punto en el infinito

    if x1 == x2:
        # Doubling (P1 = P2)
        m = (3 * x1 * x1 + A) * _inv_mod(2 * y1, P) % P
    else:
        # Addition (P1 != P2)
        m = (y2 - y1) * _inv_mod(x2 - x1, P) % P

    x3 = (m * m - x1 - x2) % P
    y3 = (m * (x1 - x3) - y1) % P

    return (x3, y3)

def _scalar_mult(k: int, point: Optional[tuple[int, int]]) -> Optional[tuple[int, int]]:
    """Multiplicación escalar k * P usando Double-and-Add."""
    k = k % N
    if k == 0 or point is None:
        return None
    
    result = None
    addend = point

    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1

    return result

class Secp256k1KeyPair(NamedTuple):
    public_key_b64: str
    private_key_b64: str

class Secp256k1Identity:
    """
    Abstracción formal para integración con CORTEX-Persist.
    Genera pares de claves secp256k1 exportados en Base64.
    """
    @staticmethod
    def generate_keypair() -> Secp256k1KeyPair:
        private_key_bytes = os.urandom(32)
        private_key = int.from_bytes(private_key_bytes, byteorder='big')
        
        private_key = private_key % N
        if private_key == 0:
            private_key = 1

        public_point = _scalar_mult(private_key, G)
        if not public_point:
            raise ValueError("Failed to generate public point")
        
        # Serialize point to bytes (uncompressed format: 0x04 + x + y)
        pub_bytes = b'\x04' + public_point[0].to_bytes(32, 'big') + public_point[1].to_bytes(32, 'big')
        priv_bytes = private_key.to_bytes(32, 'big')
        
        return Secp256k1KeyPair(
            public_key_b64=base64.b64encode(pub_bytes).decode('ascii'),
            private_key_b64=base64.b64encode(priv_bytes).decode('ascii')
        )

class Secp256k1Signer:
    """Enterprise Signer compatibility para secp256k1."""
    
    @staticmethod
    def sign_payload(private_key_b64: str, payload_hash: str, timestamp: str) -> str:
        """Sign payload hash + timestamp."""
        priv_bytes = base64.b64decode(private_key_b64)
        private_key = int.from_bytes(priv_bytes, byteorder='big')
        
        message = f"{payload_hash}:{timestamp}".encode()
        z = int.from_bytes(hashlib.sha256(message).digest(), byteorder='big')
        
        k = int.from_bytes(os.urandom(32), byteorder='big') % N
        if k == 0: k = 1

        r_point = _scalar_mult(k, G)
        if not r_point:
            raise ValueError("Invalid R point")
        r = r_point[0] % N
        if r == 0:
            raise ValueError("Invalid R value generated")

        s = (_inv_mod(k, N) * (z + r * private_key)) % N
        if s == 0:
            raise ValueError("Invalid S value generated")

        # Low-S normalization
        if s > N // 2:
            s = N - s

        # Serialize signature as 64 bytes (32 bytes r + 32 bytes s)
        sig_bytes = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
        return base64.b64encode(sig_bytes).decode('ascii')


class Secp256k1Verifier:
    """Enterprise Verifier compatibility para secp256k1."""
    
    @staticmethod
    def verify_signature(public_key_b64: str, payload_hash: str, timestamp: str, signature_b64: str) -> bool:
        pub_bytes = base64.b64decode(public_key_b64)
        if len(pub_bytes) != 65 or pub_bytes[0] != 0x04:
            return False # Invalid uncompressed public key format
            
        x = int.from_bytes(pub_bytes[1:33], byteorder='big')
        y = int.from_bytes(pub_bytes[33:65], byteorder='big')
        public_key = (x, y)
        
        sig_bytes = base64.b64decode(signature_b64)
        if len(sig_bytes) != 64:
            return False
            
        r = int.from_bytes(sig_bytes[:32], byteorder='big')
        s = int.from_bytes(sig_bytes[32:], byteorder='big')
        
        if r <= 0 or r >= N or s <= 0 or s >= N:
            return False

        message = f"{payload_hash}:{timestamp}".encode()
        z = int.from_bytes(hashlib.sha256(message).digest(), byteorder='big')

        w = _inv_mod(s, N)
        u1 = (z * w) % N
        u2 = (r * w) % N

        point1 = _scalar_mult(u1, G)
        point2 = _scalar_mult(u2, public_key)
        
        verify_point = _point_add(point1, point2)
        if verify_point is None:
            return False
        
        return verify_point[0] % N == r

if __name__ == "__main__":
    # Invariante de integración
    keys = Secp256k1Identity.generate_keypair()
    print("[C5-REAL] secp256k1 Object-Oriented Core initialized.")
    payload = "d41d8cd98f00b204e9800998ecf8427e" # dummy hash
    ts = "2026-06-28T05:00:00Z"
    
    sig = Secp256k1Signer.sign_payload(keys.private_key_b64, payload, ts)
    print(f"[*] Signature generated: {sig[:20]}...")
    
    valid = Secp256k1Verifier.verify_signature(keys.public_key_b64, payload, ts, sig)
    print(f"[+] Verification: {valid}")
    assert valid, "Epistemic Collapse: signature structural failure."
