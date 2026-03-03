"""cortex.utils.http — HTTP Retry Mixin Soberano.

Bridge Pattern (Axioma 9: Cross-Stack Synergy).

Un único lugar para retry exponencial con jitter en clientes HTTP.
Cualquier clase que haga HTTP puede heredar `HttpRetryMixin` y
obtener `_post_with_retry()` y `_get_with_retry()` sin reimplementar.

Filosofía:
- O(1) decisión por intento (no escanea listas ni dicts para retry)
- Zero-trust: solo reintenta en 429. Todo lo demás falla rápido.
- Idempotente: los métodos no tienen side-effects entre llamadas.
- Async by default: el I/O bloqueante es muerte térmica.

Usage::

    class MyClient(HttpRetryMixin):
        def __init__(self):
            # No longer requires httpx.AsyncClient here; initialized in Mixin if missing
            self._client = None
            self._provider = "my-service"

        async def call(self, url: str) -> dict:
            headers = {"Authorization": "Bearer ..."}
            return await self._post_with_retry(
                url, headers, payload={"q": "data"}
            )
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from typing import Any

from curl_cffi.requests import AsyncSession, RequestsError

logger = logging.getLogger("cortex.http")

# ─── Constants ───────────────────────────────────────────────────────────

_DEFAULT_MAX_RETRIES = 5
_DEFAULT_BASE_DELAY = 2.0  # seconds — doubles each attempt (exponential)
_DEFAULT_IMPERSONATE = "chrome120"

# Module-level CSPRNG — hardware entropy anti Thundering Herd (Ω₅)
_RNG = secrets.SystemRandom()


# ─── Mixin ───────────────────────────────────────────────────────────────


class HttpRetryMixin:
    """Soberano HTTP retry mixin — exponential backoff on 429.

    Requires subclass to provide:
    - `self._client`: `curl_cffi.requests.AsyncSession` (will be initialized if None)
    - `self._provider`: `str` (used in log messages only)
    """

    # Override in subclass if needed
    _max_retries: int = _DEFAULT_MAX_RETRIES
    _base_delay: float = _DEFAULT_BASE_DELAY
    _impersonate: str = _DEFAULT_IMPERSONATE

    @property
    def _provider(self) -> str:  # pragma: no cover
        """Provider name for logging. Override in subclass."""
        return self.__class__.__name__

    async def _ensure_client(self) -> AsyncSession:
        """Ensure an active AsyncSession is available."""
        if not hasattr(self, "_client") or self._client is None:
            self._client = AsyncSession(impersonate=self._impersonate)
        return self._client

    async def _post_with_retry(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        label: str = "POST",
    ) -> dict[str, Any]:
        """POST with exponential backoff on 429.

        Args:
            url: Full URL to POST to.
            headers: HTTP headers dict.
            payload: JSON-serializable body.
            label: Log label for this request (e.g. 'complete', 'invoke').

        Returns:
            Parsed JSON response dict.

        Raises:
            RequestsError: On non-429 failure or exhausted retries.
            ValueError: On JSON parse/key error in response.
        """
        return await self._request_with_retry("POST", url, headers, payload=payload, label=label)

    async def _get_with_retry(
        self,
        url: str,
        headers: dict[str, str],
        label: str = "GET",
    ) -> dict[str, Any]:
        """GET with exponential backoff on 429."""
        return await self._request_with_retry("GET", url, headers, payload=None, label=label)

    async def _do_http_call(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any] | None,
        label: str,
    ) -> dict[str, Any] | Exception:
        """Execute HTTP request and parse JSON. Returns Exception on 429 instead of raising."""
        client = await self._ensure_client()

        try:
            if method == "POST":
                response = await client.post(
                    url, headers=headers, json=payload
                )
            else:
                response = await client.get(
                    url, headers=headers
                )

            # curl_cffi uses .raise_for_status() like requests/httpx
            response.raise_for_status()
            return response.json()
        except RequestsError as exc:
            # Check for 429 in curl_cffi response
            if exc.response is not None and exc.response.status_code == 429:
                return exc
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unexpected response format from {self._provider} ({label})") from exc

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any] | None = None,
        label: str = "",
    ) -> dict[str, Any]:
        """Core retry engine — exponential backoff on HTTP 429.

        Zero-trust: only retries on 429. Everything else raises immediately.
        Landauer's Razor: single loop, single responsibility.
        """
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            result = await self._do_http_call(method, url, headers, payload, label)

            if not isinstance(result, Exception):
                return result

            last_exc = result
            # Check status code from RequestsError response
            is_429 = (
                isinstance(result, RequestsError)
                and result.response is not None
                and result.response.status_code == 429
            )
            if not is_429:
                raise result

            if attempt >= self._max_retries - 1:
                raise result

            base_delay_val = self._base_delay * (2 ** attempt)
            # AIROS-Ω: φ-scaled jitter — grows with retry depth
            phi_jitter = _RNG.uniform(0.1, 1.618 ** min(attempt + 1, 6))
            delay = base_delay_val + phi_jitter
            logger.warning(
                "HTTP %s 429 [%s] %s. Retry %d/%d in %.1fs...",
                method,
                self._provider,
                label,
                attempt + 1,
                self._max_retries,
                delay,
            )
            await asyncio.sleep(delay)

        raise last_exc or RuntimeError(  # pragma: no cover
            f"Retry loop exhausted for {self._provider} ({label})"
        )


# ─── Standalone function (for non-OOP clients) ──────────────────────────


async def _do_standalone_post(
    client: AsyncSession,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    provider: str,
    label: str,
) -> dict[str, Any] | Exception:
    try:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except RequestsError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            return exc
        raise
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unexpected response format from {provider} ({label})") from exc


async def post_with_retry(
    client: AsyncSession,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    provider: str = "unknown",
    label: str = "POST",
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
) -> dict[str, Any]:
    """Standalone retry helper — no inheritance needed.

    Args:
        client: A `curl_cffi.requests.AsyncSession` instance.
        url: Full URL to POST to.
        headers: HTTP headers.
        payload: JSON body.
        provider: Name for log messages.
        label: Request label for log messages.
        max_retries: Max attempts before giving up.
        base_delay: Initial backoff delay in seconds.

    Returns:
        Parsed JSON response dict.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        result = await _do_standalone_post(client, url, headers, payload, provider, label)

        if not isinstance(result, Exception):
            return result

        last_exc = result
        is_429 = (
            isinstance(result, RequestsError)
            and result.response is not None
            and result.response.status_code == 429
        )
        if not is_429:
            raise result

        if attempt >= max_retries - 1:
            raise result

        base_delay_val = base_delay * (2 ** attempt)
        # AIROS-Ω: φ-scaled jitter — grows with retry depth
        phi_jitter = _RNG.uniform(0.1, 1.618 ** min(attempt + 1, 6))
        delay = base_delay_val + phi_jitter
        logger.warning(
            "HTTP POST 429 [%s] %s. Retry %d/%d in %.1fs...",
            provider,
            label,
            attempt + 1,
            max_retries,
            delay,
        )
        await asyncio.sleep(delay)

    raise last_exc or RuntimeError(  # pragma: no cover
        f"Retry loop exhausted for {provider} ({label})"
    )
