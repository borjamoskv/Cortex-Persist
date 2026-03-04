"""
ZKORTEX — Zero-Knowledge Proof Layer for CORTEX.
La soberanía epistémica: probar sin revelar.

Exports:
    KnowledgeCommitment   — Pedersen-style commitment sobre un hecho
    ZKMembershipProof     — Prueba de pertenencia a un conjunto (Merkle)
    ZKRangeProof          — Prueba de que un valor entra en un rango
    ZKOrtexProver         — Orchestrador soberano de pruebas
    ZKOrtexVerifier       — Verificador público
    SovereignOpacityLayer — Integración con cortex.crypto.aes
"""

from cortex.zkortex.commitment import KnowledgeCommitment
from cortex.zkortex.merkle import MerkleTree, ZKMembershipProof
from cortex.zkortex.opacity_layer import SovereignOpacityLayer
from cortex.zkortex.prover import ZKOrtexProver
from cortex.zkortex.range_proof import ZKRangeProof
from cortex.zkortex.verifier import ZKOrtexVerifier

__all__ = [
    "KnowledgeCommitment",
    "ZKMembershipProof",
    "MerkleTree",
    "ZKRangeProof",
    "ZKOrtexProver",
    "ZKOrtexVerifier",
    "SovereignOpacityLayer",
]
