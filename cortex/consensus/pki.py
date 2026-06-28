# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Distributed Agent PKI (The Trust Matrix).

Enforces dynamic cryptographic identity registration over the Zenoh fabric.
Replaces static known_peers with a strictly mathematical Ed25519 registry.
"""

import base64
import json
import logging
from typing import Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger("cortex.consensus.pki")

class TrustMatrix:
    """Dynamic, thread-safe registry of Swarm Agents and their Public Keys."""
    
    def __init__(self):
        # agent_id -> Ed25519PublicKey
        self._peers: Dict[str, ed25519.Ed25519PublicKey] = {}
        # Tracks revoked agents to prevent Sybil re-entry
        self._revoked: set[str] = set()
        # Bootstrap tokens authorized by the Host for initial join
        self._valid_bootstrap_tokens: set[str] = set()
        
    def authorize_bootstrap_token(self, token: str) -> None:
        """Host authorizes a new ephemeral token for a nascent Vesicle."""
        self._valid_bootstrap_tokens.add(token)
        
    def get_known_peers(self) -> Dict[str, ed25519.Ed25519PublicKey]:
        """Provides the current peer snapshot to the BFTQuorumGuard."""
        return self._peers.copy()
        
    def get_peer_key(self, agent_id: str) -> Optional[ed25519.Ed25519PublicKey]:
        """Fetch a specific agent's public key."""
        return self._peers.get(agent_id)
        
    def revoke_agent(self, agent_id: str) -> None:
        """Terminal exclusion of an agent from the Swarm."""
        if agent_id in self._peers:
            del self._peers[agent_id]
        self._revoked.add(agent_id)
        logger.critical(f"[TrustMatrix] AGENT REVOKED: {agent_id}. Mutational rights severed.")
        
    def process_handshake(self, payload_str: str) -> bool:
        """
        Process an incoming Zenoh handshake broadcast.
        
        Expected JSON format:
        {
            "agent_id": "...",
            "public_key_b64": "...",
            "bootstrap_token": "...",
            "signature_b64": "..." # Signature of the bootstrap token + agent_id
        }
        """
        try:
            data = json.loads(payload_str)
            agent_id = data.get("agent_id")
            pub_b64 = data.get("public_key_b64")
            token = data.get("bootstrap_token")
            sig_b64 = data.get("signature_b64")
            
            if not all([agent_id, pub_b64, token, sig_b64]):
                return False
                
            if agent_id in self._revoked:
                logger.warning(f"[TrustMatrix] Rejected handshake from REVOKED agent: {agent_id}")
                return False
                
            if token not in self._valid_bootstrap_tokens:
                logger.warning(f"[TrustMatrix] Rejected handshake. Invalid/consumed bootstrap token: {token}")
                return False
                
            # Decode the public key
            try:
                pub_bytes = base64.b64decode(pub_b64)
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            except Exception as e:
                logger.warning(f"[TrustMatrix] Malformed public key from {agent_id}: {e}")
                return False
                
            # Verify the signature
            try:
                sig_bytes = base64.b64decode(sig_b64)
                message = f"{agent_id}:{token}".encode("utf-8")
                public_key.verify(sig_bytes, message)
            except InvalidSignature:
                logger.error(f"[TrustMatrix] Signature verification failed for agent: {agent_id}")
                return False
                
            # Success: Register agent and burn token
            self._peers[agent_id] = public_key
            self._valid_bootstrap_tokens.remove(token)
            
            logger.info(f"[TrustMatrix] Handshake ACCEPTED. Agent joined fabric: {agent_id}")
            return True
            
        except json.JSONDecodeError:
            return False

# Global Trust Matrix (Singleton)
trust_matrix = TrustMatrix()
