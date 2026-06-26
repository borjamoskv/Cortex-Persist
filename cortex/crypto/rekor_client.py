# [C5-REAL] Exergy-Maximized
"""
Sigstore Rekor Transparency Log Client.
Provides external cryptographic anchoring (P1) for the Sovereign Ledger.
"""

import base64
import hashlib
import json
import logging
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger("cortex.crypto.rekor")

# Default public Rekor instance
REKOR_URL = "https://rekor.sigstore.dev"

class RekorClient:
    """Client for anchoring ledger hashes in Sigstore Rekor."""
    
    def __init__(self, rekor_url: str = REKOR_URL):
        self.rekor_url = rekor_url

    def anchor_payload(self, payload_hash: str, signature_b64: str, public_key_pem: str) -> dict[str, Any] | None:
        """
        Submits a hashed record (hashedrekord) to Rekor to prove existence at a point in time.
        
        Args:
            payload_hash: The SHA-256 hash of the payload (e.g., Merkle Root or Entry Hash).
            signature_b64: Base64 encoded signature of the payload.
            public_key_pem: PEM encoded public key.
            
        Returns:
            The transparency log entry containing UUID and logIndex, or None if it fails.
        """
        # Hashedrekord schema version 0.0.1
        data = {
            "kind": "hashedrekord",
            "apiVersion": "0.0.1",
            "spec": {
                "signature": {
                    "content": signature_b64,
                    "publicKey": {
                        "content": base64.b64encode(public_key_pem.encode("utf-8")).decode("utf-8")
                    }
                },
                "data": {
                    "hash": {
                        "algorithm": "sha256",
                        "value": payload_hash
                    }
                }
            }
        }
        
        req = urllib.request.Request(
            f"{self.rekor_url}/api/v1/log/entries",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (201, 200):
                    response_body = response.read().decode("utf-8")
                    resp_json = json.loads(response_body)
                    # Rekor returns a dict where the key is the entry UUID
                    if resp_json:
                        uuid = list(resp_json.keys())[0]
                        entry = resp_json[uuid]
                        logger.info("Successfully anchored to Rekor. UUID: %s, LogIndex: %s", uuid, entry.get("logIndex"))
                        return {
                            "uuid": uuid,
                            "logIndex": entry.get("logIndex"),
                            "integratedTime": entry.get("integratedTime")
                        }
        except urllib.error.HTTPError as e:
            logger.error("HTTPError anchoring to Rekor: %s - %s", e.code, e.read().decode("utf-8"))
        except Exception as e:
            logger.error("Failed to anchor to Rekor: %s", e)
            
        return None
