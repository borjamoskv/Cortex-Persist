# [C5-REAL] Exergy-Maximized
"""LangChain Tool for RustChain Staking.

Wraps the stake_and_acquire operation for LangChain-based agents.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from cortex.integration.rustchain.client import RustChainClient
from cortex.integration.rustchain.staking import stake_and_acquire
from cortex.integration.rustchain.wallet import RustChainWallet


class StakingInput(BaseModel):
    """Input schema for staking tools."""
    skill: str = Field(description="The skill name/identifier to stake for and acquire.")
    amount: int = Field(description="The amount of RTC tokens to lock as a stake bond.")


class RustChainStakingTool(BaseTool):
    """LangChain tool to stake RTC tokens and acquire a skill."""

    name: str = "stake_and_acquire_skill"
    description: str = (
        "Stake RTC tokens to acquire a self-improvement skill. "
        "Performs pre-flight checks and returns fail-safe errors if the gate is offline."
    )
    args_schema: type[BaseModel] = StakingInput

    def __init__(self, wallet: RustChainWallet, client: RustChainClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._wallet = wallet
        self._client = client

    def _run(self, skill: str, amount: int) -> str:
        """Run the tool synchronously by spinning up a thread if the loop is running."""
        import asyncio
        import concurrent.futures

        def run_async() -> str:
            return asyncio.run(self._arun(skill, amount))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            return future.result()

    async def _arun(self, skill: str, amount: int) -> str:
        """Run the tool asynchronously."""
        try:
            result = await stake_and_acquire(self._wallet, self._client, skill, amount)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"status": "failed", "error": str(e)}, indent=2)
