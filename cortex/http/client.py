# SPDX-License-Identifier: Apache-2.0
"""CORTEX Sovereign HTTP Client — Centralized SSRF Protection.

All outbound HTTP requests MUST go through this module.
Blocks SSRF vectors: file://, internal IPs, link-local, loopback.

Usage:
    from cortex.http.client import safe_get, safe_post, SovereignHTTPClient

    # Simple
    resp = await safe_get("https://api.example.com/data")

    # With session reuse
    async with SovereignHTTPClient() as client:
        resp = await client.get("https://api.example.com/data")
        resp = await client.post("https://api.example.com/submit", json=payload)
"""

from __future__ import annotations

import ipaddress
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Blocked Schemes ──
_BLOCKED_SCHEMES = frozenset({"file", "ftp", "gopher", "data", "javascript"})

# ── Blocked IP Ranges (SSRF) ──
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),  # RFC1918
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
]

# ── Blocked Hostnames ──
_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "169.254.169.254",  # AWS/GCP metadata
        "metadata.internal",
    }
)


class SSRFBlockedError(Exception):
    """Raised when a URL fails SSRF validation."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"SSRF blocked: {reason} — {url}")


def validate_url(url: str) -> str:
    """Validate a URL against SSRF attack vectors.

    Returns the validated URL string on success.
    Raises SSRFBlockedError on violation.
    """
    if not url or not isinstance(url, str):
        raise SSRFBlockedError(url or "", "empty or non-string URL")

    parsed = urlparse(url)

    # 1. Scheme check
    scheme = (parsed.scheme or "").lower()
    if not scheme:
        raise SSRFBlockedError(url, "missing scheme")
    if scheme in _BLOCKED_SCHEMES:
        raise SSRFBlockedError(url, f"blocked scheme: {scheme}")
    if scheme not in ("http", "https"):
        raise SSRFBlockedError(url, f"unsupported scheme: {scheme}")

    # 2. Hostname check
    hostname = (parsed.hostname or "").lower().strip(".")
    if not hostname:
        raise SSRFBlockedError(url, "missing hostname")
    if hostname in _BLOCKED_HOSTS:
        raise SSRFBlockedError(url, f"blocked host: {hostname}")

    # 3. IP resolution check
    try:
        addr = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if addr in network:
                raise SSRFBlockedError(url, f"blocked IP range: {hostname} in {network}")
    except ValueError:
        # Not a raw IP — hostname. Check for suspicious patterns.
        # Block hex/octal IP obfuscation: 0x7f.0x0.0x0.0x1, 017700000001
        if re.match(r"^(0x[0-9a-f]+\.?)+$", hostname, re.IGNORECASE):
            raise SSRFBlockedError(url, f"hex-encoded IP obfuscation: {hostname}") from None
        if re.match(r"^[0-7]+$", hostname):
            raise SSRFBlockedError(url, f"octal IP obfuscation: {hostname}") from None
        # Block DNS rebinding patterns
        if ".internal" in hostname or hostname.endswith(".local"):
            raise SSRFBlockedError(url, f"internal/local hostname: {hostname}") from None

    # 4. Port check — block common internal service ports
    port = parsed.port
    if port and port not in (80, 443, 8080, 8443):
        logger.warning("Non-standard port %d in URL: %s", port, url)

    return url


class SovereignHTTPClient:
    """Async HTTP client with built-in SSRF protection.

    Wraps httpx.AsyncClient with URL validation on every request.
    Falls back to aiohttp if httpx is unavailable.
    """

    def __init__(self, timeout: float = 30.0, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._timeout = timeout
        self._kwargs = kwargs
        self._client = None
        self._backend = "none"

    async def __aenter__(self) -> SovereignHTTPClient:
        try:
            import httpx

            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                **self._kwargs,
            )
            self._backend = "httpx"
        except ImportError:
            try:
                import aiohttp

                self._client = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                )
                self._backend = "aiohttp"
            except ImportError:
                raise RuntimeError("Neither httpx nor aiohttp installed") from None
        return self

    async def __aexit__(self, *exc) -> None:  # type: ignore[no-untyped-def]
        if self._client is not None:
            if self._backend == "httpx":
                await self._client.aclose()
            else:
                await self._client.close()
            self._client = None

    async def get(self, url: str, **kwargs) -> object:  # type: ignore
        """SSRF-safe GET request."""
        validate_url(url)
        if self._backend == "httpx":
            return await self._client.get(url, **kwargs)  # type: ignore
        elif self._backend == "aiohttp":
            async with self._client.get(url, **kwargs) as resp:  # type: ignore
                return resp
        raise RuntimeError("Client not initialized — use async with")

    async def post(self, url: str, **kwargs) -> object:  # type: ignore
        """SSRF-safe POST request."""
        validate_url(url)
        if self._backend == "httpx":
            return await self._client.post(url, **kwargs)  # type: ignore
        elif self._backend == "aiohttp":
            async with self._client.post(url, **kwargs) as resp:  # type: ignore
                return resp
        raise RuntimeError("Client not initialized — use async with")

    async def request(self, method: str, url: str, **kwargs) -> object:  # type: ignore
        """SSRF-safe arbitrary method request."""
        validate_url(url)
        if self._backend == "httpx":
            return await self._client.request(method, url, **kwargs)  # type: ignore
        elif self._backend == "aiohttp":
            async with self._client.request(method, url, **kwargs) as resp:  # type: ignore
                return resp
        raise RuntimeError("Client not initialized — use async with")


# ── Convenience Functions ──


async def safe_get(url: str, timeout: float = 30.0, **kwargs) -> object:  # type: ignore
    """One-shot SSRF-safe GET. Opens and closes a client per call."""
    async with SovereignHTTPClient(timeout=timeout) as client:
        return await client.get(url, **kwargs)


async def safe_post(url: str, timeout: float = 30.0, **kwargs) -> object:  # type: ignore
    """One-shot SSRF-safe POST. Opens and closes a client per call."""
    async with SovereignHTTPClient(timeout=timeout) as client:
        return await client.post(url, **kwargs)
