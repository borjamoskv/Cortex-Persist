"""CORTEX MCP Toolbox Bridge — External Database Connectivity.

Provides a bridge between CORTEX and Google's MCP Toolbox for Databases,
enabling agents to query external databases (PostgreSQL, AlloyDB, MySQL,
Spanner) through a secure, centralized control plane.

Also exposes CORTEX's own knowledge base via the Toolbox membrane
(read-only, port 5050) with antifragile fallback to direct ORM.

Integrated via the `toolbox-core` Python SDK.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "DEFAULT_SERVER_URL",
    "ToolboxBridge",
    "ToolboxConfig",
    "cortex_self_bridge",
    "create_toolbox_bridge",
    "toolbox_health_check",
]

logger = logging.getLogger("cortex.mcp.toolbox_bridge")

DEFAULT_SERVER_URL = "http://127.0.0.1:5050"

_TOOLBOX_AVAILABLE = False
try:
    from toolbox_core import ToolboxClient  # type: ignore

    _TOOLBOX_AVAILABLE = True
except ImportError:
    ToolboxClient = None  # type: ignore
    logger.debug("Toolbox SDK not installed. Skip if external DBs are not required.")


# ─── Configuration ────────────────────────────────────────────────────


@dataclass
class ToolboxConfig:
    """Configuration for connecting to an MCP Toolbox server."""

    server_url: str = DEFAULT_SERVER_URL
    toolset: str = ""
    timeout_seconds: float = 30.0
    allowed_server_urls: list[str] = field(
        default_factory=lambda: [DEFAULT_SERVER_URL, "http://localhost:5050"]
    )

    @classmethod
    def from_env(cls) -> ToolboxConfig:
        """Create config from environment variables (TOOLBOX_ prefixed)."""
        allowed_raw = os.environ.get("TOOLBOX_ALLOWED_URLS", "")
        allowed = (
            [url.strip() for url in allowed_raw.split(",")]
            if allowed_raw
            else [DEFAULT_SERVER_URL, "http://localhost:5050"]
        )

        return cls(
            server_url=os.environ.get("TOOLBOX_URL", DEFAULT_SERVER_URL),
            toolset=os.environ.get("TOOLBOX_TOOLSET", ""),
            timeout_seconds=float(os.environ.get("TOOLBOX_TIMEOUT", "30")),
            allowed_server_urls=allowed,
        )


# ─── Bridge ───────────────────────────────────────────────────────────


class ToolboxBridge:
    """Bridge between CORTEX and an MCP Toolbox server.

    Centralizes connectivity to external database toolboxes for ADK agents.
    """

    def __init__(self, config: ToolboxConfig | None = None) -> None:
        self.config = config or ToolboxConfig.from_env()
        self._client: Any | None = None
        self._tools: list[Any] = []

    @property
    def is_available(self) -> bool:
        """Check if Toolbox SDK requirements are met."""
        return _TOOLBOX_AVAILABLE

    def _validate_server_url(self) -> None:
        """Enforce allowlist boundaries for external server connections."""
        url = self.config.server_url.rstrip("/")
        allowed = [u.rstrip("/") for u in self.config.allowed_server_urls]

        if url not in allowed:
            logger.critical(
                "Sovereign Security Breach: Rejected unallowed Toolbox URL: %s",
                url,
            )
            raise ValueError(
                f"External URL '{url}' not in the allowlist. "
                f"For security, update TOOLBOX_ALLOWED_URLS."
            )

    async def connect(self) -> bool:
        """Initialize connection to the Toolbox server and load schemas."""
        if not _TOOLBOX_AVAILABLE:
            logger.warning("Toolbox SDK missing. Connect aborted.")
            return False

        self._validate_server_url()

        try:
            self._client = ToolboxClient(self.config.server_url)  # type: ignore[reportOptionalCall]

            # Load tools (all or specific set)
            load_coro = (
                self._client.load_toolset(  # type: ignore[reportOptionalMemberAccess]
                    self.config.toolset,
                )
                if self.config.toolset
                else self._client.load_toolset()  # type: ignore[reportOptionalMemberAccess]
            )
            self._tools = await load_coro

            logger.info(
                "Toolbox Sync: [OK] %s | Tools: %d",
                self.config.server_url,
                len(self._tools),
            )
            return True
        except (ConnectionError, RuntimeError) as exc:
            logger.error("Toolbox Sync: [FAILED] %s | Error: %s", self.config.server_url, exc)
            self._client = None
            self._tools = []
            return False

    @property
    def tools(self) -> list[Any]:
        """Expose loaded tools for ADK agent consumption."""
        return list(self._tools)

    @property
    def tool_names(self) -> list[str]:
        """Names of tools available on the remote bridge."""
        return [getattr(t, "name", str(t)) for t in self._tools]

    async def close(self) -> None:
        """Gracefully release bridge resources."""
        if self._client:
            try:
                await self._client.close()
            except ConnectionError:
                pass
        self._client = None
        self._tools = []

    def __repr__(self) -> str:
        status = "connected" if self._client else "disconnected"
        n = len(self._tools)
        return f"ToolboxBridge({status}, tools={n}, url={self.config.server_url})"


# ─── Factory ──────────────────────────────────────────────────────────


async def create_toolbox_bridge(
    server_url: str | None = None,
    toolset: str = "",
) -> ToolboxBridge:
    """Sovereign factory for rapid bridge deployment."""
    config = ToolboxConfig.from_env()

    if server_url:
        config.server_url = server_url
        if server_url not in config.allowed_server_urls:
            config.allowed_server_urls.append(server_url)

    if toolset:
        config.toolset = toolset

    bridge = ToolboxBridge(config)
    await bridge.connect()
    return bridge


async def cortex_self_bridge(
    toolset: str = "cortex-readonly",
) -> ToolboxBridge | None:
    """Connect to the local CORTEX Toolbox membrane.

    Returns a bridge pre-configured for reading CORTEX's own
    knowledge base, or None if the server is unreachable
    (antifragile fallback — callers degrade to direct ORM).

    Tools via cortex-readonly:
      query-facts, query-ghosts, query-decisions,
      query-signals, cortex-stats
    """
    if not toolbox_health_check():
        logger.warning(
            "Toolbox membrane unreachable at %s — fallback to direct ORM.",
            DEFAULT_SERVER_URL,
        )
        return None
    return await create_toolbox_bridge(
        server_url=DEFAULT_SERVER_URL,
        toolset=toolset,
    )


def toolbox_health_check(
    url: str = DEFAULT_SERVER_URL,
    timeout: float = 2.0,
) -> bool:
    """Probe whether the Toolbox server is alive.

    Uses stdlib urllib — zero external deps. Hits GET /api/toolset/
    and expects a 200 response within `timeout` seconds.
    """
    import urllib.error
    import urllib.request

    probe = f"{url.rstrip('/')}/api/toolset/"
    try:
        req = urllib.request.Request(probe, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except (urllib.error.URLError, OSError, TimeoutError):
        return False
