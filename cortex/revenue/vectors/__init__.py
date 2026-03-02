"""CORTEX Revenue Vectors — Pluggable income pipelines."""

from __future__ import annotations

__all__ = [
    "MicroSaaSVector",
    "ArbitrageVector",
    "OutreachVector",
]


def __getattr__(name: str):  # noqa: ANN001
    """Lazy imports."""
    if name == "MicroSaaSVector":
        from cortex.revenue.vectors.microsaas import MicroSaaSVector
        return MicroSaaSVector
    if name == "ArbitrageVector":
        from cortex.revenue.vectors.arbitrage import ArbitrageVector
        return ArbitrageVector
    if name == "OutreachVector":
        from cortex.revenue.vectors.outreach import OutreachVector
        return OutreachVector
    raise AttributeError(f"module 'cortex.revenue.vectors' has no attribute {name!r}")
