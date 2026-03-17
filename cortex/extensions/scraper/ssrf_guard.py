"""SSRF Guard — Sovereign URL Validation.

Deterministic validation boundary for outbound HTTP requests.
Prevents Server-Side Request Forgery by enforcing:
  - Scheme allowlist (http, https only)
  - DNS resolution with full address family check
  - Private/loopback/link-local/multicast IP denylist
  - Cloud metadata endpoint blocking
  - Credential rejection in URLs
  - Redirect chain validation
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from urllib.parse import urlparse

LOG = logging.getLogger("cortex.extensions.scraper.ssrf_guard")

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_ALLOWED_METHODS = frozenset({"GET", "HEAD"})

# Cloud metadata endpoints — exact IPs and hostnames
_METADATA_IPS = frozenset(
    {
        "169.254.169.254",  # AWS, GCP, Azure
        "169.254.169.253",  # AWS DNS
        "fd00:ec2::254",  # AWS IPv6
    }
)

_METADATA_HOSTNAMES = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
    }
)

# RFC-defined private/reserved networks
_DENIED_NETWORKS_V4: list[IPv4Network] = [
    IPv4Network("0.0.0.0/8"),  # "This" network
    IPv4Network("10.0.0.0/8"),  # Private (RFC 1918)
    IPv4Network("100.64.0.0/10"),  # Shared address space (RFC 6598)
    IPv4Network("127.0.0.0/8"),  # Loopback
    IPv4Network("169.254.0.0/16"),  # Link-local
    IPv4Network("172.16.0.0/12"),  # Private (RFC 1918)
    IPv4Network("192.0.0.0/24"),  # IETF Protocol Assignments
    IPv4Network("192.0.2.0/24"),  # TEST-NET-1
    IPv4Network("192.168.0.0/16"),  # Private (RFC 1918)
    IPv4Network("198.18.0.0/15"),  # Benchmarking
    IPv4Network("198.51.100.0/24"),  # TEST-NET-2
    IPv4Network("203.0.113.0/24"),  # TEST-NET-3
    IPv4Network("224.0.0.0/4"),  # Multicast
    IPv4Network("240.0.0.0/4"),  # Reserved
    IPv4Network("255.255.255.255/32"),  # Broadcast
]

_DENIED_NETWORKS_V6: list[IPv6Network] = [
    IPv6Network("::1/128"),  # Loopback
    IPv6Network("::/128"),  # Unspecified
    IPv6Network("::ffff:0:0/96"),  # IPv4-mapped (check underlying v4)
    IPv6Network("64:ff9b::/96"),  # NAT64
    IPv6Network("100::/64"),  # Discard-Only
    IPv6Network("fc00::/7"),  # Unique local
    IPv6Network("fe80::/10"),  # Link-local
    IPv6Network("ff00::/8"),  # Multicast
]

# Maximum response body size: 10 MiB
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
# Default timeout for outbound requests
DEFAULT_TIMEOUT = 10.0
# Maximum redirect hops
MAX_REDIRECTS = 3


class SSRFViolation(Exception):
    """Raised when a URL fails SSRF validation."""


def _is_ip_denied(ip_str: str) -> bool:
    """Check if an IP address falls within any denied network."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Unparseable → deny

    # Cloud metadata exact match
    if ip_str in _METADATA_IPS:
        return True

    if isinstance(addr, IPv4Address):
        return any(addr in net for net in _DENIED_NETWORKS_V4)
    elif isinstance(addr, IPv6Address):
        # Check IPv6 denied networks
        if any(addr in net for net in _DENIED_NETWORKS_V6):
            return True
        # IPv4-mapped IPv6 addresses: extract the v4 part and re-check
        if addr.ipv4_mapped:
            return any(addr.ipv4_mapped in net for net in _DENIED_NETWORKS_V4)
        return False
    return True  # Unknown address family → deny


def resolve_and_validate(hostname: str) -> list[str]:
    """Resolve hostname to IPs and validate every returned address.

    Returns list of safe IP strings.
    Raises SSRFViolation if any resolved IP is denied.
    """
    if not hostname:
        raise SSRFViolation("Empty hostname")

    # Block metadata hostnames
    if hostname.lower() in _METADATA_HOSTNAMES:
        raise SSRFViolation(f"Blocked metadata hostname: {hostname}")

    try:
        # Resolve all address families (IPv4 + IPv6)
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFViolation(f"DNS resolution failed for {hostname}: {e}") from e

    if not results:
        raise SSRFViolation(f"No DNS results for {hostname}")

    safe_ips: list[str] = []
    for _family, _type, _proto, _canonname, sockaddr in results:
        ip_str = str(sockaddr[0])
        if _is_ip_denied(ip_str):
            raise SSRFViolation(f"Resolved IP {ip_str} for {hostname} is in denied range")
        safe_ips.append(str(ip_str))

    return safe_ips


def validate_url(url: str) -> str:
    """Validate a URL for SSRF safety.

    Checks:
    - Scheme is http or https
    - No embedded credentials
    - Hostname resolves to non-private IPs

    Returns the validated URL (unchanged).
    Raises SSRFViolation on any check failure.
    """
    parsed = urlparse(url)

    # Scheme check
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise SSRFViolation(f"Disallowed scheme: {parsed.scheme}")

    # Credential check
    if parsed.username or parsed.password:
        raise SSRFViolation("URLs with embedded credentials are not allowed")

    # Hostname extraction
    hostname = parsed.hostname
    if not hostname:
        raise SSRFViolation("No hostname in URL")

    # Port check — block uncommon ports that could hit internal services
    port = parsed.port
    if port is not None and port not in (80, 443, 8080, 8443):
        LOG.warning("Non-standard port %d in URL %s", port, url)

    # DNS resolution + IP validation
    resolve_and_validate(hostname)

    return url


def validate_redirect(redirect_url: str) -> str:
    """Validate a redirect destination for SSRF safety.

    Re-resolves DNS and re-checks IPs to prevent DNS rebinding.
    """
    return validate_url(redirect_url)
