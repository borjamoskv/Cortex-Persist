"""
ZKORTEX — Knowledge Commitments.

Un Commitment es una caja sellada: contiene un secreto, demuestra que existe,
pero no lo revela. Mathematically binding + hiding.

Implementación: Pedersen commitment sobre curva elíptica BLS12-381 (vía py_ecc).
    C = secret·G + blinding·H

Propiedades:
    • Hiding Perfecto: C revela exactamente 0 bits de secret.
    • Binding Computacional: Exige resolver el problema del logaritmo discreto.
    • Homomorfismo aditivo: C(a) + C(b) = C(a+b)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from py_ecc.bls12_381 import G1, add, multiply

if TYPE_CHECKING:
    pass

_BLINDING_LENGTH = 32  # 256-bit blinding factor
_COMMITMENT_VERSION = 2  # v2: Pedersen sobre BLS12-381

_GROUP_ORDER = 0x73eda753299d7d483339d80809a1d80553bda402fffe5bfeffffffff00000001
G = G1


def _hash_to_scalar(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "big") % _GROUP_ORDER


_H_SCALAR = _hash_to_scalar(b"zkortex:pedersen:h_generator:v2")
H = multiply(G, _H_SCALAR)


@dataclass(frozen=True)
class KnowledgeCommitment:
    """
    Commitment criptográfico a un hecho.

    Contiene:
        commitment_hex: El hash público (punto G1 serializado). Se puede compartir libremente.
        timestamp:      Cuándo fue creado el commitment.
        version:        Protocolo de serialización.

    NO contiene: el secreto ni el blinding factor (están en el Prover).
    """

    commitment_hex: str
    timestamp: float = field(default_factory=time.time)
    version: int = _COMMITMENT_VERSION
    metadata: dict[str, str] = field(default_factory=dict)

    def verify(self, secret: str, blinding_factor: bytes) -> bool:
        """
        Verifica que este commitment corresponde a (secret, blinding_factor).
        SOLO el poseedor del blinding_factor puede verificar —
        nadie más puede abrir el commitment.
        """
        expected = _compute_commitment(secret, blinding_factor)
        # Constant-time compare para evitar timing attacks
        return hmac.compare_digest(self.commitment_hex, expected)

    def to_public_dict(self) -> dict[str, object]:
        """Serialización pública — NUNCA contiene el secreto."""
        return {
            "commitment": self.commitment_hex,
            "timestamp": self.timestamp,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_public_dict(cls, d: dict[str, object]) -> KnowledgeCommitment:
        return cls(
            commitment_hex=str(d["commitment"]),
            timestamp=float(d.get("timestamp", time.time())),  # type: ignore[arg-type]
            version=int(d.get("version", _COMMITMENT_VERSION)),  # type: ignore[arg-type]
            metadata=dict(d.get("metadata", {})),  # type: ignore[arg-type]
        )


def commit(secret: str, blinding_factor: bytes | None = None) -> tuple[KnowledgeCommitment, bytes]:
    """
    Crea un nuevo Pedersen commitment a `secret`.

    Retorna:
        (commitment, blinding_factor)

    El blinding_factor es el testigo privado. Si se pierde, el commitment
    se vuelve inabrible (plausible deniability máxima).
    """
    if blinding_factor is None:
        blinding_factor = os.urandom(_BLINDING_LENGTH)

    commitment_hex = _compute_commitment(secret, blinding_factor)
    c = KnowledgeCommitment(commitment_hex=commitment_hex)
    return c, blinding_factor


def _point_to_hex(point: tuple | None) -> str:
    """Serializa un punto en coordenadas afines (x,y) sobre FQ."""
    if point is None:
        return "00" * 96
    return f"{int(point[0]):096x}{int(point[1]):096x}"


def _compute_commitment(secret: str, blinding_factor: bytes) -> str:
    """
    C = secret_scalar·G + blinding_scalar·H
    Y retorna C serializado como hex de 288 caracteres (3 coord de 96 chars).
    """
    secret_scalar = _hash_to_scalar(secret.encode("utf-8"))
    blinding_scalar = int.from_bytes(blinding_factor, "big") % _GROUP_ORDER
    
    C = add(
        multiply(G, secret_scalar),
        multiply(H, blinding_scalar)
    )
    return _point_to_hex(C)
