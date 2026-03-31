"""CORTEX Security Guards — Network & Filesystem Boundary Enforcement.

Fail-closed validators for SSRF prevention, path traversal prevention,
and exception sanitization. All guards are designed to be imported and
used across the codebase wherever user-controlled input touches network
or filesystem operations.
"""

from __future__ import annotations

import ipaddress
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("cortex.security.guards")

# Private/reserved IP ranges that MUST NOT be reachable via user input
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("0.0.0.0/8"),  # "This" network
]

_ALLOWED_SCHEMES = {"http", "https"}


def is_private_ip(host: str) -> bool:
    """Check if a hostname resolves to a private/reserved IP range.

    Returns True if the host is a private IP or resolves to one.
    For hostnames that cannot be resolved, returns True (fail-closed).
    """
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # It's a hostname, not an IP — resolve it
        import socket

        try:
            resolved = socket.getaddrinfo(host, None, socket.AF_UNSPEC)
            for _, _, _, _, sockaddr in resolved:
                ip_str = sockaddr[0]
                try:
                    addr = ipaddress.ip_address(ip_str)
                    if any(addr in net for net in _BLOCKED_NETWORKS) or addr.is_private:
                        return True
                except ValueError:
                    return True  # Fail-closed
            return False
        except (socket.gaierror, OSError):
            return True  # Fail-closed: can't resolve = block

    return any(addr in net for net in _BLOCKED_NETWORKS) or addr.is_private


def validate_url(url: str) -> str:
    """Validate URL is safe for server-side requests (SSRF prevention).

    Returns the validated URL string.
    Raises ValueError if the URL is unsafe.
    """
    parsed = urlparse(url)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Blocked scheme: {parsed.scheme!r} (allowed: {_ALLOWED_SCHEMES})")

    host = parsed.hostname
    if not host:
        raise ValueError("URL has no hostname")

    if is_private_ip(host):
        logger.warning("SSRF BLOCKED: %s resolves to private IP", url)
        raise ValueError(f"SSRF blocked: {host!r} resolves to private/reserved IP")

    return url


def validate_path(user_path: str, base_dir: str | Path) -> Path:
    """Validate a user-provided path stays within base_dir (path traversal prevention).

    Returns the resolved, validated Path.
    Raises ValueError if the path escapes the base directory.
    """
    base = Path(base_dir).resolve()
    resolved = (base / user_path).resolve()

    if not str(resolved).startswith(str(base) + os.sep) and resolved != base:
        logger.warning("PATH TRAVERSAL BLOCKED: %s escapes %s", user_path, base)
        raise ValueError(f"Path traversal blocked: {user_path!r} escapes {base}")

    return resolved


def sanitize_exception(exc: Exception) -> str:
    """Sanitize exception for safe external exposure.

    Strips stack traces, file paths, and internal details.
    Returns a generic error message safe for API responses.
    """
    # Map known exception types to safe messages
    safe_messages = {
        "FileNotFoundError": "The requested resource was not found.",
        "PermissionError": "Access denied.",
        "ConnectionError": "External service temporarily unavailable.",
        "TimeoutError": "The operation timed out.",
        "ValueError": "Invalid input provided.",
    }

    exc_type = type(exc).__name__
    safe_msg = safe_messages.get(exc_type)
    if safe_msg:
        return safe_msg

    # For unknown exceptions, return generic message
    # Log the real error internally
    logger.error("Sanitized exception [%s]: %s", exc_type, exc, exc_info=True)
    return "An internal error occurred. Please try again later."
