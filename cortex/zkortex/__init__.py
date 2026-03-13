"""
ZKORTEX — Zero-Knowledge Proof Layer for CORTEX.
La soberanía epistémica: probar sin revelar.

Uses __getattr__ lazy loading to avoid cascading import failures
from optional dependencies (py_ecc via commitment/prover modules).

Exports:
    KnowledgeCommitment   — Pedersen-style commitment sobre un hecho
    ZKMembershipProof     — Prueba de pertenencia a un conjunto (Merkle)
    ZKRangeProof          — Prueba de que un valor entra en un rango
    ZKOrtexProver         — Orchestrador soberano de pruebas
    ZKOrtexVerifier       — Verificador público
    SovereignOpacityLayer — Integración con cortex.crypto.aes
"""

from __future__ import annotations

import importlib

__all__ = [
    "KnowledgeCommitment",
    "MerkleTree",
    "SovereignOpacityLayer",
    "ZKMembershipProof",
    "ZKOrtexProver",
    "ZKOrtexVerifier",
    "ZKRangeProof",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "KnowledgeCommitment": ("cortex.zkortex.commitment", "KnowledgeCommitment"),
    "MerkleTree": ("cortex.zkortex.merkle", "MerkleTree"),
    "ZKMembershipProof": ("cortex.zkortex.merkle", "ZKMembershipProof"),
    "SovereignOpacityLayer": ("cortex.zkortex.opacity_layer", "SovereignOpacityLayer"),
    "ZKOrtexProver": ("cortex.zkortex.prover", "ZKOrtexProver"),
    "ZKRangeProof": ("cortex.zkortex.range_proof", "ZKRangeProof"),
    "ZKOrtexVerifier": ("cortex.zkortex.verifier", "ZKOrtexVerifier"),
}


def __getattr__(name: str) -> object:
    """Lazy-load zkortex symbols on first access (PEP 562)."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.zkortex' has no attribute {name!r}")
