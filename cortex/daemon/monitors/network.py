"""Site monitoring for MOSKV daemon."""

from __future__ import annotations

import logging
import time

import httpx

from cortex.daemon.models import (
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_BACKOFF,
    SiteStatus,
)

logger = logging.getLogger("moskv-daemon")


class SiteMonitor:
    """Checks URL availability with retry and backoff."""

    def __init__(
        self,
        urls: list[str],
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ):
        self.urls = urls
        self.timeout = timeout
        self.retries = retries

    def check_all(self) -> list[SiteStatus]:
        """Check all URLs. Returns list of SiteStatus."""
        return [self._check_one(url) for url in self.urls]

    def _check_one(self, url: str) -> SiteStatus:
        """Check a single URL with retry and backoff."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        last_error = ""

        for attempt in range(self.retries + 1):
            try:
                start = time.monotonic()
                resp = httpx.get(url, timeout=self.timeout)
                elapsed = (time.monotonic() - start) * 1000
                healthy = resp.status_code < 400
                return SiteStatus(
                    url=url,
                    healthy=healthy,
                    status_code=resp.status_code,
                    response_ms=elapsed,
                    checked_at=now,
                    error="" if healthy else f"HTTP {resp.status_code}",
                )
            except httpx.TimeoutException:
                last_error = "timeout"
            except httpx.ConnectError:
                last_error = "connection refused"
            except httpx.HTTPError as e:
                last_error = str(e)

            logger.debug("Retry %d/%d for %s (%s)", attempt + 1, self.retries, url, last_error)
            time.sleep(RETRY_BACKOFF)

        return SiteStatus(
            url=url,
            healthy=False,
            status_code=0,
            response_ms=0,
            checked_at=now,
            error=last_error,
        )
