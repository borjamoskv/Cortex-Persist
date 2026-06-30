# [C5-REAL] Exergy-Maximized
"""RustChain Staking & Judge Integration.

Provides wrappers and tools to implement the RustChain open staking SDK,
MCP Staking tools, and Open Judge gates.
"""

from __future__ import annotations

from babylon60.integration.rustchain.client import RustChainClient
from babylon60.integration.rustchain.judge import (
    ASTLintJudge,
    Judge,
    PolicyJudge,
    TestRunnerJudge,
)
from babylon60.integration.rustchain.mcp_tool import register_rustchain_tools
from babylon60.integration.rustchain.staking import (
    GateUnavailableError,
    StakingError,
    stake_and_acquire,
)
from babylon60.integration.rustchain.wallet import RustChainWallet

__all__ = [
    "RustChainClient",
    "RustChainWallet",
    "stake_and_acquire",
    "StakingError",
    "GateUnavailableError",
    "register_rustchain_tools",
    "Judge",
    "ASTLintJudge",
    "TestRunnerJudge",
    "PolicyJudge",
]
