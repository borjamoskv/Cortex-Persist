# [C5-REAL] Exergy-Maximized
"""MCP Tools for RustChain Staking.

Exposes stake_and_acquire as an MCP tool on FastMCP.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from cortex.integration.rustchain.client import RustChainClient
from cortex.integration.rustchain.staking import stake_and_acquire
from cortex.integration.rustchain.wallet import RustChainWallet

logger = logging.getLogger("cortex.integration.rustchain.mcp_tool")


def register_rustchain_tools(
    mcp: FastMCP,
    wallet: Optional[RustChainWallet] = None,
    client: Optional[RustChainClient] = None,
) -> None:
    """Registers RustChain staking tools on a FastMCP server instance."""

    # Lazily initialize default client and wallet if not provided
    active_client = client or RustChainClient()
    active_wallet = wallet or RustChainWallet.create()

    @mcp.tool()
    async def stake_and_acquire_skill(skill: str, amount: int) -> str:
        """
        Stake RTC tokens to acquire a self-improvement skill.

        Args:
            skill: The skill identifier/name (e.g., 'fast_ast_parsing').
            amount: The amount of RTC tokens to lock.
        """
        logger.info("Executing stake_and_acquire_skill for %s with %d RTC", skill, amount)
        try:
            result = await stake_and_acquire(active_wallet, active_client, skill, amount)
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error("Staking tool execution failed: %s", e)
            return json.dumps({"status": "failed", "error": str(e)}, indent=2)
