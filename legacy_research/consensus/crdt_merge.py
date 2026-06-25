import logging

import cortex_rs

logger = logging.getLogger(__name__)

class CRDTMergeEngine:
    """
    Python bridge to the C5-REAL Rust CRDTMergeState implementation.
    Guarantees Commutativity, Associativity, and Idempotency in parameter merging.
    """
    def __init__(self):
        self._rs_engine = cortex_rs.CRDTMergeState() # type: ignore
        
    def add_model(self, model_hash: str, agent_id: str, epoch_time: int) -> None:
        self._rs_engine.add_model(model_hash, agent_id, epoch_time)
        
    def remove_model(self, model_hash: str) -> None:
        self._rs_engine.remove_model(model_hash)
        
    def merge_from_peer(self, peer_state_json: str) -> None:
        try:
            self._rs_engine.merge_with_json(peer_state_json)
        except Exception as e:
            logger.error(f"Failed to merge peer state: {e}")
            raise

    def get_state_json(self) -> str:
        return self._rs_engine.get_state_json()
        
    def get_active_models(self) -> list[str]:
        return self._rs_engine.get_active_models()
        
    def get_merkle_hash(self) -> str:
        return self._rs_engine.get_merkle_hash()


class MAPElitesGossipListener:
    """
    Listener for the asynchronous Gossip protocol required for DEI (Diversity in Evolutionary Inference).
    """
    def __init__(self, merge_engine: CRDTMergeEngine):
        self.merge_engine = merge_engine
        
    async def listen(self, peer_stream):
        """Asynchronous listener for MAP-Elites gossip."""
        async for peer_state in peer_stream:
            self.merge_engine.merge_from_peer(peer_state)
            logger.debug(f"Merged peer state, new Merkle hash: {self.merge_engine.get_merkle_hash()}")
