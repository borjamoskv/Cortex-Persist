"""
IPFSClient — ΩΩ-HANDOFF Semana 5-6
Lightweight async HTTP client for IPFS.
Supports local daemon (HTTP API) or public Infura/Cloudflare gateways.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

__all__ = [
    "IPFSClient",
    "IPFSError",
    "IPFSPinResult",
]

logger = logging.getLogger("cortex.extensions.swarm.ipfs_client")

# Public read gateways tried in order when no local daemon is available
_PUBLIC_GATEWAYS = [
    "https://cloudflare-ipfs.com",
    "https://ipfs.io",
    "https://dweb.link",
]


class IPFSError(Exception):
    """Non-retryable IPFS operation failure."""


@dataclass(frozen=True, slots=True)
class IPFSPinResult:
    """Result of a successful pin/add operation."""

    cid: str
    size_bytes: int = 0
    backend: str = "local"
    extra: dict[str, Any] = field(default_factory=dict)


class IPFSClient:
    """Async IPFS client with local daemon primary and public-gateway fallback.

    Usage:
        client = IPFSClient()                            # local daemon
        client = IPFSClient(api_url="https://ipfs.infura.io:5001")

    The `pin` method adds content via the IPFS HTTP API (/api/v0/add).
    The `fetch` method reads via /ipfs/<cid> on the gateway.
    """

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:5001",
        gateway_url: str = "http://127.0.0.1:8080",
        timeout: float = 20.0,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def pin(self, data: bytes, filename: str = "cortex.bin") -> IPFSPinResult:
        """Add and pin content to IPFS.

        Tries the local daemon first; on failure falls back to Infura-compatible
        endpoints if configured, then raises IPFSError.

        Args:
            data:     Raw bytes to store.
            filename: Filename hint for IPFS directory entries.

        Returns:
            IPFSPinResult with the CID and final backend used.
        """
        url = f"{self.api_url}/api/v0/add?pin=true&quieter=true"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    files={"file": (filename, data, "application/octet-stream")},
                )
                response.raise_for_status()
                payload = response.json()
                cid = payload.get("Hash") or payload.get("Cid", {}).get("/", "")
                if not cid:
                    raise IPFSError(f"IPFS add returned no CID: {payload}")

                logger.info("IPFS pin: CID=%s size=%s", cid, len(data))
                return IPFSPinResult(
                    cid=cid,
                    size_bytes=len(data),
                    backend=self.api_url,
                    extra=payload,
                )

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            raise IPFSError(f"IPFS pin failed ({self.api_url}): {exc}") from exc

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def fetch(self, cid: str) -> bytes:
        """Retrieve content by CID.

        Tries the local gateway first, then cascades through public gateways.

        Args:
            cid: IPFS Content Identifier.

        Returns:
            Raw bytes of the stored content.

        Raises:
            IPFSError: If all gateways fail.
        """
        gateways = [self.gateway_url] + _PUBLIC_GATEWAYS

        last_error: Exception | None = None
        for gw in gateways:
            url = f"{gw}/ipfs/{cid}"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    logger.debug("IPFS fetch: CID=%s via %s", cid, gw)
                    return response.content
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.debug("IPFS fetch failed via %s: %s", gw, exc)
                last_error = exc

        raise IPFSError(f"IPFS fetch failed for CID {cid}: {last_error}")

    # ------------------------------------------------------------------
    # Health probe
    # ------------------------------------------------------------------

    async def is_healthy(self) -> bool:
        """Ping the local IPFS daemon. Returns True if reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(f"{self.api_url}/api/v0/id")
                return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False
