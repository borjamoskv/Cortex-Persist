# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Byzantine Fault Tolerance (BFT) Quorum Guard.

Enforces INV_BFT_QUORUM: No payload is authorized for Ledger anchoring
unless at least N/3 nodes in the Swarm fabric have signed it.
"""

import logging
from typing import Dict, List, Set

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger("cortex.consensus.bft_quorum")

class BFTQuorumGuard:
    """Enforces Byzantine Quorum (N/3) for Zenoh/Swarm mutations."""
    
    def __init__(self, known_peers: Dict[str, ed25519.Ed25519PublicKey]):
        """
        Initialize with a registry of known peer public keys.
        
        Args:
            known_peers: Mapping of agent_id to their Ed25519 public keys.
        """
        self.known_peers = known_peers
        
    def authorize_payload(self, payload: bytes, signatures: Dict[str, bytes]) -> bool:
        """
        Validates if a payload has enough valid signatures to meet the N/3 BFT quorum.
        
        Args:
            payload: The raw bytes of the proposed mutation/CRDT.
            signatures: Mapping of agent_id to their signature of the payload.
            
        Returns:
            bool: True if authorized (>= N/3 valid signatures), False otherwise.
        """
        if not self.known_peers:
            # If no peers are registered, we run in standalone mode, but we log a warning.
            logger.warning("[BFT_QUORUM] No known peers registered. Running in standalone fallback.")
            return True
            
        total_nodes = len(self.known_peers)
        required_quorum = max(1, total_nodes // 3)
        
        valid_count = 0
        valid_signers: Set[str] = set()
        
        for agent_id, sig_bytes in signatures.items():
            if agent_id not in self.known_peers:
                logger.warning(f"[BFT_QUORUM] Signature from unknown agent: {agent_id}")
                continue
                
            pub_key = self.known_peers[agent_id]
            
            try:
                pub_key.verify(sig_bytes, payload)
                valid_signers.add(agent_id)
                valid_count += 1
                
                # Fast exit if quorum is met
                if valid_count >= required_quorum:
                    logger.info(f"[BFT_QUORUM] Quorum met ({valid_count}/{total_nodes}) for payload.")
                    return True
                    
            except InvalidSignature:
                logger.warning(f"[BFT_QUORUM] Invalid signature from agent: {agent_id}")
                
        logger.critical(
            f"[BFT_QUORUM] Quorum NOT met. Only {valid_count}/{required_quorum} valid signatures."
        )
        return False
