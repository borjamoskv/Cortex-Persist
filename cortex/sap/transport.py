"""CORTEX v5.0 — SAP OData Transport Layer.

Manages HTTP connection lifecycles, exponential backoff, and exception mapping.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from cortex.sap.models import SAPAuthError, SAPConfig, SAPConnectionError, SAPEntityError
from cortex.sap.vault import SAPVault

__all__ = ["SAPTransport"]

logger = logging.getLogger("cortex.sap.transport")


class SAPTransport:
    """HTTP client specialized in SAP OData resiliency and I/O."""

    def __init__(self, config: SAPConfig, vault: SAPVault) -> None:
        self.config = config
        self.vault = vault
        self._http: httpx.AsyncClient | None = None

    @property
    def is_connected(self) -> bool:
        """Check if the transport is actively listening."""
        return self._http is not None

    async def connect(self) -> None:
        """Initialize HTTP client and negotiate initial CSRF token."""
        if self._http:
            return

        self._http = httpx.AsyncClient(
            timeout=self.config.timeout,
            verify=True,
        )

        auth_headers = await self.vault.get_auth_headers(self._http)

        # Fetch CSRF token via HEAD on service root
        try:
            resp = await self._http.head(
                self.config.base_url_normalized,
                headers={
                    **auth_headers,
                    "x-csrf-token": "Fetch",
                    **self.config.headers,
                },
            )
        except httpx.ConnectError as e:
            await self.close()
            msg = f"Cannot reach SAP at {self.config.base_url}: {e}"
            raise SAPConnectionError(msg) from e

        if resp.status_code == 401:
            await self.close()
            raise SAPAuthError("SAP authentication failed — check credentials")
        if resp.status_code == 403:
            await self.close()
            raise SAPAuthError("SAP authorization denied — check permissions")
        if resp.status_code >= 400:
            err = resp.text[:200]
            await self.close()
            raise SAPConnectionError(f"SAP connection error: HTTP {resp.status_code} — {err}")

        token = resp.headers.get("x-csrf-token", "")
        if token:
            self.vault.set_csrf_token(token)

        logger.info("Connected to SAP at %s (CSRF: %s)", self.config.base_url_normalized, bool(token))

    async def close(self) -> None:
        """Close the underlying HTTP connection."""
        if self._http:
            await self._http.aclose()
            self._http = None
        self.vault.clear()

    async def request(
        self,
        method: str,
        url_path: str,
        *,
        params: dict[str, str] | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        """Execute JSON OData request with automatic retry and parsing.

        Args:
            method: HTTP verb.
            url_path: Full URL path to hit.
            params: Query string dict.
            json_data: Optional payload.

        Returns:
            Parsed JSON dict, or empty dict for 204 No Content.
        """
        resp = await self.raw_request(method, url_path, params=params, json_data=json_data)

        if resp.status_code == 204:
            return {}

        try:
            return resp.json()
        except (OSError, RuntimeError):
            return {"raw": resp.text[:500]}

    async def raw_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json_data: dict | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with exponential backoff and transparent auth injections."""
        if not self._http:
            raise SAPConnectionError("Transport is closed — call connect() first")

        auth_headers = await self.vault.get_auth_headers(self._http)
        headers = self.vault.build_request_headers(method, auth_headers, json_data is not None)

        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                resp = await self._http.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )
                self._check_response_status(resp)
                return resp
            except (SAPAuthError, SAPEntityError):
                raise
            except (httpx.RequestError, OSError, RuntimeError) as e:
                last_error = e
                await self._handle_retry_wait(attempt)

        raise SAPConnectionError(
            f"SAP request failed after {self.config.max_retries} retries: {last_error}"
        )

    @staticmethod
    def _check_response_status(resp: httpx.Response) -> None:
        """Raise strongly-typed exception for specific HTTP fault codes."""
        if resp.status_code == 401:
            raise SAPAuthError("Authentication expired — reconnect required")
        if resp.status_code == 403:
            raise SAPAuthError(f"Forbidden: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise SAPEntityError(f"SAP error {resp.status_code}: {resp.text[:300]}")

    async def _handle_retry_wait(self, attempt: int) -> None:
        """Sleep using exponential backoff on retry iteration. Skips last attempt wait."""
        if attempt >= self.config.max_retries - 1:
            return

        wait = 2**attempt
        logger.warning(
            "SAP transport fault. Retrying %d/%d in %ds",
            attempt + 1, self.config.max_retries, wait,
        )
        await asyncio.sleep(wait)
