"""True Heartbeat Monitor.

A true heartbeat should calculate the hash of the entropy on each poll
and alert solely when the semantic asymmetry deviates from the given threshold.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from cortex.daemon.models import SiteStatus

logger = logging.getLogger("cortex.monitors.heartbeat")


class TrueHeartbeatMonitor:
    """Heartbeat monitor using semantic drift instead of status == 200."""

    def __init__(
        self,
        target_url: str,
        threshold: float = 0.05,
        check_interval: int = 60,
    ):
        self.target_url = target_url
        self.threshold = threshold
        self.check_interval = check_interval
        self.past = ""
        self.is_running = False

    def _hash_entropy(self, payload: str) -> str:
        """Calculate the hash of the entropy payload."""
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def semantic_drift(self, current: str, past: str) -> float:
        """Calculate the semantic asymmetry (drift) between two entropy hashes."""
        if not past:
            return 0.0

        current_hash = self._hash_entropy(current)
        past_hash = self._hash_entropy(past)

        diff = sum(c1 != c2 for c1, c2 in zip(current_hash, past_hash, strict=False))
        return float(diff) / max(len(current_hash), 1)

    async def poll(self, session: Any) -> SiteStatus:
        """Poll the endpoint and measure semantic drift."""
        import time

        now = datetime.now(timezone.utc).isoformat()

        try:
            start = time.monotonic()
            async with session.get(self.target_url) as response:
                current_payload = await response.text()
                elapsed = (time.monotonic() - start) * 1000

                # Core Logic: replace status==200 with semantic_drift > threshold
                drift = self.semantic_drift(current_payload, self.past)

                if drift > self.threshold:
                    msg = (
                        f"Semantic drift detected ({drift:.2f} > {self.threshold})"
                        f" on {self.target_url}"
                    )
                    logger.warning(msg)
                    healthy = False
                    error = "Semantic asymmetry deviated threshold"
                else:
                    healthy = True
                    error = ""

                self.past = current_payload

                return SiteStatus(
                    url=self.target_url,
                    healthy=healthy,
                    status_code=response.status,
                    response_ms=elapsed,
                    checked_at=now,
                    error=error,
                )
        except (OSError, RuntimeError) as e:
            logger.error("Failed to poll %s: %s", self.target_url, e)
            return SiteStatus(
                url=self.target_url,
                healthy=False,
                status_code=0,
                response_ms=0.0,
                checked_at=now,
                error=str(e),
            )
