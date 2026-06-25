# [C5-REAL] Exergy-Maximized
"""
The ZK-Swarm Retrieval Guard (RFC-003 Phase 1)

Enforces cryptographic integrity over agent inference outputs before they mutate
the Sovereign Ledger. Limits hallucination ('stochastic entropy') by verifying
mathematical proofs of consensus encoded inside the fact metadata.
"""

import hashlib
import os
import json
from typing import Any

from cortex.crypto.keys import ZKSwarmIdentity


class VoidStateSecurityError(Exception):
    """Raised when an active fact mathematically fails the ZK-Swarm cryptographic proof."""


class ZKSwarmGuard:
    """The local engine verification point for Subagent Ed25519 signatures."""

    def __init__(self, enforce_on_types: tuple[str, ...] = ("decision", "rule", "code")) -> None:
        """
        Args:
            enforce_on_types: The topological subset of nodes demanding high-rigor checking.
                              Passive nodes like 'knowledge' or 'memory' may bypass.
        """
        self._enforce_on_types = enforce_on_types

    async def verify_integrity(self, content: str, fact_type: str, meta: dict[str, Any]) -> None:
        """
        Intercepts incoming facts and runs the formal validation logic (RFC-003).

        Args:
            content: The raw string extracted from the inference engine.
            fact_type: 'decision', 'rule', 'chat', etc.
            meta: Metadata payload expected to contain Byzantine signature tokens.

        Raises:
            VoidStateSecurityError: if validation boundaries are mathematically violated.
        """
        if fact_type not in self._enforce_on_types:
            # Low exergy topological type -> standard stochastic heuristic handling
            return

        public_key_b64 = meta.get("agent_public_key")
        signature_b64 = meta.get("zk_proof_signature")

        if not public_key_b64 or not signature_b64:
            raise VoidStateSecurityError(
                f"[ZK-SWARM] Missing cryptographic proof for high-risk topological type '{fact_type}'. "
                "Agent must sign the inference payload via Ed25519."
            )

        # Byzantine Fault Tolerance: local verification of the execution proof
        is_valid = ZKSwarmIdentity.verify_payload(
            content=content, public_key_b64=public_key_b64, signature_b64=signature_b64
        )

        if not is_valid:
            raise VoidStateSecurityError(
                f"[ZK-SWARM] Cryptographic signature INVALID for payload of type '{fact_type}'. "
                "Potential hallucination, manipulation, or thermodynamic fault detected."
            )

class CommitRevealProtocol:
    """
    Zero-Knowledge Epistemic Contention using Commit-Reveal schemes (SHA3-256).
    Enables swarm agents to prove precedence/causality of a fact without exposing its 
    decrypted contents during the ingestion phase, maintaining multi-tenant isolation.
    """
    
    @staticmethod
    def generate_commit(payload_dict: dict, secret_nonce: bytes = None) -> tuple[str, str]: # type: ignore
        """
        Generates a SHA3-256 commitment of the payload.
        Returns (commit_hash_hex, secret_nonce_hex).
        """
        if secret_nonce is None:
            secret_nonce = os.urandom(32)
            
        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode('utf-8')
        
        hasher = hashlib.sha3_256()
        hasher.update(secret_nonce)
        hasher.update(payload_bytes)
        
        commit_hash = hasher.hexdigest()
        return commit_hash, secret_nonce.hex()
        
    @staticmethod
    def verify_commit(commit_hash: str, secret_nonce_hex: str, payload_dict: dict) -> bool:
        """
        Verifies that a payload and a secret nonce match the previously generated commit hash.
        """
        try:
            secret_nonce = bytes.fromhex(secret_nonce_hex)
        except ValueError:
            return False
            
        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode('utf-8')
        
        hasher = hashlib.sha3_256()
        hasher.update(secret_nonce)
        hasher.update(payload_bytes)
        
        expected_hash = hasher.hexdigest()
        return expected_hash == commit_hash
