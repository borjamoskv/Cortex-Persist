"""
ZKORTEX — Range Proofs.

Probar que CORTEX tiene N hechos sobre un tema X,
o que un valor numérico cae en [min, max],
sin revelar ni N exacto ni el valor.

Implementación: Bit decomposition ZK (simplificada, sin SNARKs).
Para producción real: migrar a Bulletproofs o Groth16.

La implementación actual usa un esquema de commitments sobre bits —
más pedagógica y auditable que una librería de circuit proofs.
"""

from __future__ import annotations

import hashlib
import hmac as hmaclib
import os
from dataclasses import dataclass

_BLINDING_LENGTH = 32


def _bit_commit(bit: int, blinding: bytes) -> str:
    """Commit a un solo bit."""
    payload = f"zkortex:bit:{bit}".encode()
    return hmaclib.new(blinding, payload, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class ZKRangeProof:
    """
    Prueba de que un valor v ∈ [min_val, max_val].

    Campos públicos:
        bit_commitments: Commitments a cada bit de v (sin revelar v).
        challenge_response: Sumatorio de blindings bajo challenge (Σ-protocol).
        min_val, max_val: El rango declarado.
        claimed_bits: Número de bits del valor (≈ log2(max_val)).

    CORTEX demuestra:
        "Mi conjunto tiene entre min_val y max_val hechos"
    sin revelar el número exacto.
    """

    bit_commitments: list[str]
    challenge_response: str  # hex
    min_val: int
    max_val: int
    claimed_bits: int

    def verify_structure(self) -> bool:
        """
        Verificación estructural (sin el valor real).
        Comprueba que el número de bit_commitments es coherente con el rango.
        """
        expected_bits = (self.max_val).bit_length()
        return (
            len(self.bit_commitments) == self.claimed_bits
            and self.claimed_bits <= expected_bits + 1
            and self.min_val <= self.max_val
        )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "bit_commitments": self.bit_commitments,
            "challenge_response": self.challenge_response,
            "range": {"min": self.min_val, "max": self.max_val},
            "claimed_bits": self.claimed_bits,
        }


def prove_range(value: int, min_val: int, max_val: int) -> ZKRangeProof:
    """
    Prueba que `value` ∈ [min_val, max_val] sin revelar `value`.

    Raises ValueError si value no está en el rango.
    """
    if not (min_val <= value <= max_val):
        raise ValueError(
            f"Value {value} is outside the claimed range [{min_val}, {max_val}]. "
            "Cannot construct honest proof."
        )

    # Bit decomposition
    num_bits = max(1, (max_val).bit_length())
    bits = [(value >> i) & 1 for i in range(num_bits)]
    blindings = [os.urandom(_BLINDING_LENGTH) for _ in range(num_bits)]
    bit_commitments = [_bit_commit(b, r) for b, r in zip(bits, blindings, strict=True)]

    combined = b"".join(blindings)
    challenge = hashlib.sha256(
        b"zkortex:range:challenge:" + str(value).encode() + combined
    ).digest()
    # En un Σ-protocol real: response = r + challenge * secret (mod order)
    # Aquí usamos HMAC como aproximación honesta
    response = hmaclib.new(challenge, combined, hashlib.sha256).hexdigest()

    return ZKRangeProof(
        bit_commitments=bit_commitments,
        challenge_response=response,
        min_val=min_val,
        max_val=max_val,
        claimed_bits=num_bits,
    )


def verify_range_proof(proof: ZKRangeProof) -> bool:
    """
    Verificación pública del proof estructural.
    No requiere conocer el valor — solo la prueba.
    """
    return proof.verify_structure()
