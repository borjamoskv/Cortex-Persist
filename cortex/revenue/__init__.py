"""CORTEX Revenue Engine — Autonomous Revenue Generation.

DINERO-Ω: Three zero-capital income vectors orchestrated by a sovereign engine.

Vectors:
    V1: Micro-SaaS Factory — auto-build and deploy paid tools
    V2: Arbitrage Scanner — price discrepancy detection
    V3: B2B Web Design Pipeline — automated outreach with Awwwards-grade design
"""

from __future__ import annotations

__all__ = [
    "RevenueEngine",
    "Opportunity",
    "ExecutionResult",
    "RevenueReport",
    "RevenueVector",
]


def __getattr__(name: str):  # noqa: ANN001
    """Lazy imports to avoid heavy startup cost."""
    if name == "RevenueEngine":
        from cortex.revenue.engine import RevenueEngine
        return RevenueEngine
    if name in ("Opportunity", "ExecutionResult", "RevenueReport", "RevenueVector"):
        from cortex.revenue import models
        return getattr(models, name)
    raise AttributeError(f"module 'cortex.revenue' has no attribute {name!r}")
