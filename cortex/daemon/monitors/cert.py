"""SSL certificate monitor for MOSKV daemon."""

from __future__ import annotations

import logging
import socket
import ssl
from datetime import datetime, timezone

from cortex.daemon.models import DEFAULT_CERT_WARN_DAYS, DEFAULT_TIMEOUT, CertAlert

logger = logging.getLogger("moskv-daemon")


class CertMonitor:
    """Checks SSL certificate expiry for hostnames."""

    def __init__(
        self,
        hostnames: list[str],
        warn_days: int = DEFAULT_CERT_WARN_DAYS,
    ):
        self.hostnames = hostnames
        self.warn_days = warn_days

    def check(self) -> list[CertAlert]:
        """Return alerts for certs expiring within warn_days."""
        alerts: list[CertAlert] = []
        for hostname in self.hostnames:
            alert = self._check_one(hostname)
            if alert:
                alerts.append(alert)
        return alerts

    def _check_one(self, hostname: str) -> CertAlert | None:
        """Check a single hostname's SSL certificate."""
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=DEFAULT_TIMEOUT) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    not_after = cert.get("notAfter", "")
                    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(
                        tzinfo=timezone.utc
                    )
                    days_left = (expires - datetime.now(timezone.utc)).days
                    if days_left < self.warn_days:
                        return CertAlert(
                            hostname=hostname,
                            expires_at=expires.isoformat(),
                            days_remaining=days_left,
                        )
        except OSError as e:
            logger.warning("SSL check failed for %s: %s", hostname, e)
        return None
