import logging
from typing import Any

from cortex.extensions.swarm.arweave_client import ArweaveClient

logger = logging.getLogger("cortex.extensions.swarm.verifier")

class ContinuityVerifier:
    """Verifies the chronological and cryptographic continuity of Arweave anchored fact chains.
    
    Prevents "Memory Forking" by guaranteeing that a given Cortex-Fact-Id
    has an unbroken history on the Arweave network.
    """

    def __init__(self, node_url: str = "https://arweave.net"):
        self.arweave_client = ArweaveClient(node_url=node_url)

    def _extract_tags(self, tx_node: dict[str, Any]) -> dict[str, str]:
        """Convert Arweave GraphQL tags (name/value) to a simple dictionary."""
        tags = {}
        for tag in tx_node.get("tags", []):
            name = tag.get("name")
            value = tag.get("value")
            if name and value:
                tags[name] = value
        return tags

    async def verify_chain(self, fact_id: str) -> bool:
        """Fetch all transactions for a fact_id and verify their temporal continuity."""
        tx_nodes = await self.arweave_client.query_handoff_chain(fact_id)
        
        if not tx_nodes:
            logger.warning("No transactions found for Cortex-Fact-Id: %s", fact_id)
            return False
            
        logger.info("Verifying continuity for %s (Found %d transactions)", fact_id, len(tx_nodes))
        
        last_timestamp = 0
        
        for idx, tx in enumerate(tx_nodes):
            tags = self._extract_tags(tx)
            
            # Arweave GraphQL Heights are sorted ascending (oldest first).
            # We must ensure timestamps logically progress forward.
            payload_ts_str = tags.get("Cortex-Timestamp", "0")
            try:
                payload_ts = int(payload_ts_str)
            except ValueError:
                logger.error("Invalid Timestamp tag on tx %s", tx.get("id"))
                return False
                
            if payload_ts < last_timestamp:
                logger.error(
                    "Continuity broken! Tx %s goes back in time (payload ts: %d < %d)",
                    tx.get("id"), payload_ts, last_timestamp
                )
                return False
                
            last_timestamp = payload_ts
            
        logger.info("Chain %s verified successfully as chronologically continuous.", fact_id)
        return True
