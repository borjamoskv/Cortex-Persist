"""CORTEX Agent Runtime — MCP Configuration Loader.

Parses an `mcp_servers.json` configuration file, compatible
with standard MCP clients (like Claude Desktop), returning
dataclasses to boot stdio client servers.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("cortex.agents.mcp_config")

__all__ = ["McpServerConfig", "load_mcp_config"]

DEFAULT_CONFIG_PATH = "mcp_servers.json"


@dataclass
class McpServerConfig:
    """Configuration for an external MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


def load_mcp_config(config_path: str = DEFAULT_CONFIG_PATH) -> list[McpServerConfig]:
    """Load MCP server definitions from a JSON file.

    Format expected:
    {
      "mcpServers": {
        "stripe": {
          "command": "npx",
          "args": ["-y", "@stripe/mcp"],
          "env": {"STRIPE_API_KEY": "sk_test_..."}
        }
      }
    }

    Returns:
        List of McpServerConfig objects. Returns empty list if file not found
        or if JSON structure is missing "mcpServers".
    """
    path = Path(config_path)
    if not path.is_file():
        logger.debug("MCP config not found at %s. Proceeding without MCP servers.", path)
        return []

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as exc:
        logger.error("Failed to parse MCP config %s: %s", path, exc)
        return []

    servers_dict = data.get("mcpServers", {})
    if not isinstance(servers_dict, dict):
        logger.warning("'mcpServers' key is not a dictionary in %s", path)
        return []

    configs: list[McpServerConfig] = []
    base_env = dict(os.environ)

    for name, params in servers_dict.items():
        if not isinstance(params, dict):
            continue

        cmd = params.get("command")
        if not cmd:
            logger.warning("MCP server '%s' missing 'command'. Skipping.", name)
            continue

        args = params.get("args", [])
        env_overrides = params.get("env", {})

        # Merge base environment with specific env (so the stdio command doesn't lack PATH etc)
        merged_env = base_env.copy()
        if isinstance(env_overrides, dict):
            merged_env.update(env_overrides)

        configs.append(
            McpServerConfig(
                name=name,
                command=cmd,
                args=args if isinstance(args, list) else [],
                env=merged_env,
            )
        )

    logger.info("Loaded %d MCP servers from %s", len(configs), path)
    return configs
