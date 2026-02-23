"""CORTEX MCP Toolbox Bridge — External Database Connectivity.

Provides a bridge between CORTEX and Google's MCP Toolbox for Databases,
enabling agents to query external databases (PostgreSQL, AlloyDB, MySQL,
Spanner) through a secure, centralized control plane.

Integrated via the `toolbox-core` Python SDK.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cortex.mcp.toolbox_bridge")

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

    server_url: str = "http://127.0.0.1:5000"
    toolset: str = ""
    timeout_seconds: float = 30.0
    allowed_server_urls: list[str] = field(
        default_factory=lambda: ["http://127.0.0.1:5000", "http://localhost:5000"]
    )

    @classmethod
    def from_env(cls) -> ToolboxConfig:
        """Create config from environment variables (TOOLBOX_ prefixed)."""
        allowed_raw = os.environ.get("TOOLBOX_ALLOWED_URLS", "")
        allowed = (
            [url.strip() for url in allowed_raw.split(",")]
            if allowed_raw
            else ["http://127.0.0.1:5000", "http://localhost:5000"]
        )

        return cls(
            server_url=os.environ.get("TOOLBOX_URL", "http://127.0.0.1:5000"),
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
            logger.critical("Sovereign Security Breach: Rejected unallowed Toolbox URL: %s", url)
            raise ValueError(
                f"External URL '{url}' not in TOOLBOX_ALLOWED_URLS. For security, update configuration."
            )

    async def connect(self) -> bool:
        """Initialize connection to the Toolbox server and load schemas."""
        if not _TOOLBOX_AVAILABLE:
            logger.warning("Toolbox SDK missing. Connect aborted.")
            return False

        self._validate_server_url()

        try:
            self._client = ToolboxClient(self.config.server_url)

            # Load tools (all or specific set)
            load_coro = (
                self._client.load_toolset(self.config.toolset)
                if self.config.toolset
                else self._client.load_toolset()
            )
            self._tools = await load_coro

            logger.info(
                "Toolbox Sync: [OK] %s | Tools: %d",
                self.config.server_url,
                len(self._tools),
            )
            return True
        except (ConnectionError, OSError, RuntimeError) as exc:
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
            except (ConnectionError, OSError):
                pass
        self._client = None
        self._tools = []

    def __repr__(self) -> str:
        status = "ACTIVE" if self._client else "IDLE"
        return f"ToolboxBridge(status={status}, tools={len(self._tools)}, url={self.config.server_url})"


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
