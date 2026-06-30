# [C5-REAL] Exergy-Maximized
"""
Sigstore Rekor Client.

Interacts with the public Sigstore transparency log to provide third-party
cryptographic verifiable proof of existence for ledger entries.
"""

import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger("babylon60.audit.rekor")

REKOR_URL = "https://rekor.sigstore.dev/api/v1/log/entries"


class RekorClient:
    """Client for Sigstore Rekor Transparency Log."""

    def __init__(self, rekor_url: str = REKOR_URL) -> None:
        self.rekor_url = rekor_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def log_entry(
        self, entry_hash: str, signature_hex: str, public_key_pem: bytes
    ) -> str | None:
        """
        Submits a hashedrekord to the Rekor transparency log.

        Args:
            entry_hash: The SHA-256 hash of the entry.
            signature_hex: The signature in hex format.
            public_key_pem: The public key in PEM format.

        Returns:
            The Rekor entry UUID if successful, None otherwise.
        """
        # Rekor expects the signature content to be base64 encoded.
        try:
            sig_bytes = bytes.fromhex(signature_hex)
            sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
            pk_b64 = base64.b64encode(public_key_pem).decode("utf-8")

            payload = {
                "kind": "hashedrekord",
                "apiVersion": "0.0.1",
                "spec": {
                    "signature": {"content": sig_b64, "publicKey": {"content": pk_b64}},
                    "data": {"hash": {"algorithm": "sha256", "value": entry_hash}},
                },
            }

            response = await self._client.post(self.rekor_url, json=payload)

            if response.status_code == 201:
                data = response.json()
                if data and isinstance(data, dict):
                    return list(data.keys())[0]
            elif response.status_code == 409:
                data = response.json()
                if data and isinstance(data, dict):
                    return list(data.keys())[0]
            else:
                logger.error(
                    f"[Rekor] Failed to log entry. Status: {response.status_code}, Body: {response.text}"
                )
                return None

        except Exception as e:  # noqa: BLE001
            logger.error(f"[Rekor] Exception during log_entry: {e}")
            return None

    async def verify_entry(self, rekor_uuid: str) -> dict[str, Any] | None:
        """
        Fetches an entry from Rekor to verify inclusion.
        """
        try:
            response = await self._client.get(f"{self.rekor_url}/{rekor_uuid}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"[Rekor] Failed to fetch entry {rekor_uuid}. Status: {response.status_code}"
                )
                return None
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Rekor] Exception fetching entry: {e}")
            return None
