"""
[C5-REAL] SOBERANÍA MATEMÁTICA: ELLIPTIC CURVE CRYPTOGRAPHY (secp256k1)
Implementación determinista y estructural para CORTEX-Persist.
Erradicación de "Black Boxes" criptográficas.

El grupo secp256k1 se define como:
y^2 = x^3 + 7 (mod p)

Author: borjamoskv (SYS_ID: borjamoskv)
"""

import hashlib
import os

# --- PARÁMETROS DEL DOMINIO secp256k1 ---
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
A = 0
B = 7
G_X = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
G_Y = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (G_X, G_Y)

def inv_mod(k, p):
    """Inverso multiplicativo modular vía el Teorema Pequeño de Fermat: k^(p-2) mod p"""
    if k == 0:
        raise ZeroDivisionError('Division by zero in finite field.')
    return pow(k, p - 2, p)

def point_add(p1, p2):
    """Suma de puntos P1 + P2 en la curva elíptica secp256k1."""
    if p1 is None: return p2
    if p2 is None: return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 != y2:
        return None  # Punto en el infinito

    if x1 == x2:
        # Doubling (P1 = P2)
        m = (3 * x1 * x1 + A) * inv_mod(2 * y1, P) % P
    else:
        # Addition (P1 != P2)
        m = (y2 - y1) * inv_mod(x2 - x1, P) % P

    x3 = (m * m - x1 - x2) % P
    y3 = (m * (x1 - x3) - y1) % P

    return (x3, y3)

def scalar_mult(k, point):
    """Multiplicación escalar k * P usando Double-and-Add."""
    k = k % N
    if k == 0 or point is None:
        return None
    
    result = None
    addend = point

    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1

    return result

def generate_keypair():
    """Generación de par de claves C5-REAL."""
    # Obtener entropía nativa del OS
    private_key_bytes = os.urandom(32)
    private_key = int.from_bytes(private_key_bytes, byteorder='big')
    
    # Asegurar que la clave está en el rango [1, N-1]
    private_key = private_key % N
    if private_key == 0:
        private_key = 1

    # Derivar clave pública: Pub = priv * G
    public_key = scalar_mult(private_key, G)
    return private_key, public_key

def sha256_hash(data: bytes) -> int:
    """Hash determinista para firmas."""
    return int.from_bytes(hashlib.sha256(data).digest(), byteorder='big')

def ecdsa_sign(private_key, message_hash):
    """Firma ECDSA cruda sobre secp256k1."""
    z = message_hash
    k = int.from_bytes(os.urandom(32), byteorder='big') % N
    if k == 0: k = 1

    r, _ = scalar_mult(k, G)
    r = r % N
    if r == 0:
        raise ValueError("Invalid R value generated")

    s = (inv_mod(k, N) * (z + r * private_key)) % N
    if s == 0:
        raise ValueError("Invalid S value generated")

    # Low-S normalization (BIP-62)
    if s > N // 2:
        s = N - s

    return (r, s)

def ecdsa_verify(public_key, message_hash, signature):
    """Verificación de firma ECDSA estructural."""
    r, s = signature
    if r <= 0 or r >= N or s <= 0 or s >= N:
        return False

    w = inv_mod(s, N)
    u1 = (message_hash * w) % N
    u2 = (r * w) % N

    point1 = scalar_mult(u1, G)
    point2 = scalar_mult(u2, public_key)
    
    verify_point = point_add(point1, point2)
    
    if verify_point is None:
        return False
    
    return verify_point[0] % N == r

if __name__ == "__main__":
    # Test de Invariante Causal
    print("[C5-REAL] Initiating secp256k1 ECC Core...")
    priv, pub = generate_keypair()
    print(f"[*] Private Key (Hex): {hex(priv)}")
    print(f"[*] Public Key X:      {hex(pub[0])}")
    print(f"[*] Public Key Y:      {hex(pub[1])}")

    msg = b"Ontologia Cero - CORTEX Persist v10.0"
    msg_hash = sha256_hash(msg)
    
    sig = ecdsa_sign(priv, msg_hash)
    print(f"\n[*] Signature R:       {hex(sig[0])}")
    print(f"[*] Signature S:       {hex(sig[1])}")

    is_valid = ecdsa_verify(pub, msg_hash, sig)
    print(f"\n[+] Signature Valid?   {is_valid}")
    assert is_valid, "Epistemic Collapse: Signature validation failed."
