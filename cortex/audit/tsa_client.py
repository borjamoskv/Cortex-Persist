"""
RFC3161 Timestamp Authority (TSA) Client.

Interacts with a public TSA to obtain a cryptographically
signed timestamp token over the Master Ledger's Merkle Roots.
"""

import base64
import logging
from typing import Optional

import httpx

try:
    import rfc3161ng  # pyright: ignore[reportMissingImports] # Opt-in  # pyright: ignore[reportMissingImports] # Opt-in secure dependency
except ImportError:
    rfc3161ng = None

logger = logging.getLogger("cortex.audit.tsa")

DEFAULT_TSA_URL = "http://timestamp.digicert.com"


class TSAClient:
    """Client for RFC3161 Timestamp Authorities."""

    def __init__(self, tsa_url: str = DEFAULT_TSA_URL) -> None:
        self.tsa_url = tsa_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def get_timestamp_token(self, payload_hash: str) -> Optional[str]:
        """
        Sends an RFC3161 Timestamp Request for the given SHA-256 hash.

        Args:
            payload_hash: The SHA-256 hex string to timestamp.

        Returns:
            The raw timestamp token base64 encoded if successful, None otherwise.
        """
        if not rfc3161ng:
            logger.warning("[TSA] rfc3161ng is not installed. Returning mocked token.")
            return base64.b64encode(b"MOCK_TSA_" + payload_hash.encode("utf-8")).decode("ascii")

        try:
            req = rfc3161ng.make_request(payload_hash.encode("utf-8"), hash_algo="sha256")

            response = await self._client.post(
                self.tsa_url, content=req, headers={"Content-Type": "application/timestamp-query"}
            )

            if response.status_code == 200:
                return base64.b64encode(response.content).decode("ascii")
            else:
                logger.error(f"[TSA] Failed to retrieve token. Status: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"[TSA] Exception during get_timestamp_token: {e}")
            return None
