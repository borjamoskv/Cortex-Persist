# [C5-REAL] Exergy-Maximized
"""
ZKORTEX - Zero-Knowledge Proof Layer for CORTEX.
Epistemic sovereignty: proving without revealing.

Uses __getattr__ lazy loading to avoid cascading import failures
from optional dependencies (py_ecc via commitment/prover modules).

Exports:
    KnowledgeCommitment   - Pedersen-style commitment over a fact
    ZKMembershipProof     - Proof of membership in a set (Merkle)
    ZKRangeProof          - Proof that a value falls within a range
    ZKOrtexProver         - Sovereign orchestrator of proofs
    ZKOrtexVerifier       - Public verifier
    SovereignOpacityLayer - Integration with cortex.crypto.aes
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.zkortex.commitment import KnowledgeCommitment
    from cortex.extensions.zkortex.merkle import MerkleTree, ZKMembershipProof
    from cortex.extensions.zkortex.opacity_layer import SovereignOpacityLayer
    from cortex.extensions.zkortex.prover import ZKOrtexProver
    from cortex.extensions.zkortex.range_proof import ZKRangeProof
    from cortex.extensions.zkortex.verifier import ZKOrtexVerifier

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
    "KnowledgeCommitment": ("cortex_extensions.zkortex.commitment", "KnowledgeCommitment"),
    "MerkleTree": ("cortex_extensions.zkortex.merkle", "MerkleTree"),
    "ZKMembershipProof": ("cortex_extensions.zkortex.merkle", "ZKMembershipProof"),
    "SovereignOpacityLayer": ("cortex_extensions.zkortex.opacity_layer", "SovereignOpacityLayer"),
    "ZKOrtexProver": ("cortex_extensions.zkortex.prover", "ZKOrtexProver"),
    "ZKRangeProof": ("cortex_extensions.zkortex.range_proof", "ZKRangeProof"),
    "ZKOrtexVerifier": ("cortex_extensions.zkortex.verifier", "ZKOrtexVerifier"),
}


def __getattr__(name: str) -> object:
    """Lazy-load zkortex symbols on first access (PEP 562)."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex_extensions.zkortex' has no attribute {name!r}")
