"""URL Security Guard — SSRF Prevention.

Blocks access to local, private, or restricted IP ranges and ensures only
standard protocols (http/https) are used.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

LOG = logging.getLogger("cortex.guards.url_guard")

# Default blocked IP ranges (RFC1918, Private, Local, Multicast, etc.)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private-use (Class A)
    ipaddress.ip_network("172.16.0.0/12"),  # Private-use (Class B)
    ipaddress.ip_network("192.168.0.0/16"),  # Private-use (Class C)
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 Loopback
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-local
    ipaddress.ip_network("fc00::/7"),  # IPv6 Unique Local
]

# Additional safety for cloud metadata (AWS, GCP, Azure)
CLOUD_METADATA_IP = "169.254.169.254"


def is_safe_url(url: str, allowed_schemes: list[str] | None = None) -> bool:
    """Check if a URL is safe for extraction (no SSRF)."""
    if not allowed_schemes:
        allowed_schemes = ["http", "https"]

    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            LOG.warning("🚫 [URL_GUARD] Invalid scheme: %s", parsed.scheme)
            return False

        if not parsed.netloc:
            LOG.warning("🚫 [URL_GUARD] No hostname in URL: %s", url)
            return False

        # Check for numeric IP addresses directly
        hostname = parsed.hostname
        if not hostname:
            return False

        try:
            # Try parsing as IP address directly
            ip = ipaddress.ip_address(hostname)
            if any(ip in net for net in BLOCKED_NETWORKS):
                LOG.warning("🚫 [URL_GUARD] Blocked IP (direct): %s", ip)
                return False
        except ValueError:
            # Not an IP address, proceed to DNS resolution check
            pass

        # Resolve hostname to IPs and check each
        try:
            # Note: This is a synchronous blocking call, which is fine for guards,
            # but we perform it only when necessary.
            addresses = socket.getaddrinfo(hostname, None)
            for addr in addresses:
                ip_str = addr[4][0]
                ip = ipaddress.ip_address(ip_str)
                if any(ip in net for net in BLOCKED_NETWORKS):
                    LOG.warning("🚫 [URL_GUARD] Blocked IP (resolved): %s -> %s", hostname, ip)
                    return False
        except (socket.gaierror, socket.herror) as e:
            LOG.warning("🚫 [URL_GUARD] DNS resolution failed for %s: %s", hostname, e)
            return False

        return True

    except Exception as e:
        LOG.error("❌ [URL_GUARD] Critical error checking %s: %s", url, e)
        return False
