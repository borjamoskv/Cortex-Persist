import base64
import hashlib
import json
import logging
import time
from typing import Any

import httpx

from cortex.engine.causality import LedgerEvent
from cortex.extensions.swarm.identity import IdentityAnchor

logger = logging.getLogger("cortex.extensions.swarm.arweave_client")

class ArweaveClient:
    """Lightweight client for anchoring CORTEX events to Arweave/Irys."""

    def __init__(self, node_url: str = "https://arweave.net"):
        self.node_url = node_url.rstrip("/")

    @staticmethod
    def _create_tag(name: str, value: str) -> dict[str, str]:
        """Create a Base64URL encoded Arweave tag."""
        return {
            "name": base64.urlsafe_b64encode(name.encode("utf-8")).decode("ascii").rstrip("="),
            "value": base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("="),
        }

    def prepare_handoff_transaction(
        self, event: LedgerEvent, anchor: IdentityAnchor
    ) -> dict[str, Any]:
        """Serialize a CORTEX event, sign it, and prepare an Arweave v2 transaction."""
        
        # 1. Payload Serialization
        data = {
            "event_id": event.event_id,
            "parent_ids": sorted(event.parent_ids),
            "status": event.status.value if hasattr(event.status, "value") else event.status,
            "trust_score": event.trust_score,
            "created_at": event.created_at,
            "tainted": event.tainted,
        }
        payload_bytes = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        
        # 2. Tags
        tags = [
            self._create_tag("App-Name", "CORTEX-Ω"),
            self._create_tag("Content-Type", "application/json"),
            self._create_tag("Cortex-Fact-Id", event.event_id),
            self._create_tag("Cortex-Timestamp", str(int(time.time()))),
        ]
        
        # 3. Signature (RSA-PSS) over the payload hash.
        # Note: A real Arweave v2 transaction requires deep hash signing over tags + payload.
        # For this lightweight implementation, we sign the payload + tag hash directly.
        tag_concat = "".join(t["name"] + t["value"] for t in tags).encode("utf-8")
        signature_material = hashlib.sha256(payload_bytes + tag_concat).digest()
        signature_bytes = anchor.sign(signature_material)
        signature_b64 = base64.urlsafe_b64encode(signature_bytes).decode("ascii").rstrip("=")
        
        jwk = anchor.export_public_jwk()
        
        # 4. Generate the transaction ID (SHA-256 of the signature)
        tx_id_bytes = hashlib.sha256(signature_bytes).digest()
        tx_id_b64 = base64.urlsafe_b64encode(tx_id_bytes).decode("ascii").rstrip("=")
        
        return {
            "format": 2,
            "id": tx_id_b64,
            "last_tx": "",
            "owner": jwk["n"],
            "tags": tags,
            "target": "",
            "quantity": "0",
            "data": payload_b64,
            "data_size": str(len(payload_bytes)),
            "reward": "0",  # Bundlr/Irys or simulated local net requires different fee logic
            "signature": signature_b64,
        }

    async def anchor_handoff(self, event: LedgerEvent, anchor: IdentityAnchor) -> str | None:
        """Anchors the handoff event to the Arweave network."""
        tx = self.prepare_handoff_transaction(event, anchor)
        tx_id = tx["id"]
        
        url = f"{self.node_url}/tx"
        logger.info("Anclando Handoff %s en Arweave (TX: %s)", event.event_id, tx_id)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=tx)
                
                # Assume 200 or 202 is success. 
                if response.status_code in (200, 202, 208):
                    logger.info("Handoff anclado con éxito: %s", tx_id)
                    return tx_id
                else:
                    logger.warning("Fallo al anclar en Arweave: %s - %s", response.status_code, response.text)
                    return None
        except httpx.RequestError as e:
            logger.error("Error de conectividad anclando en Arweave: %s", e)
            return None
