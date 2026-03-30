"""Ouroboros Capital Engine.

Contains autonomous agents for zero-utility liquidity extraction,
MEV arbitrage, and fiat yield accumulation.
"""

from cortex.agents.ouroboros.strike import OuroborosStrikeAgent

__all__ = ["OuroborosStrikeAgent"]
