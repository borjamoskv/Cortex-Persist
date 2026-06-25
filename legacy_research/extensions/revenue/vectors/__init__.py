# [C5-REAL] Exergy-Maximized

from __future__ import annotations

__all__ = [
    "MicroSaaSVector",  # pyright: ignore[reportUnsupportedDunderAll]
    "ArbitrageVector",  # pyright: ignore[reportUnsupportedDunderAll]
    "OutreachVector",  # pyright: ignore[reportUnsupportedDunderAll]
]


def __getattr__(name: str):  # noqa: ANN001
    """Lazy imports."""
    if name == "MicroSaaSVector":
        from legacy_research.extensions.revenue.vectors.microsaas import MicroSaaSVector

        return MicroSaaSVector
    if name == "ArbitrageVector":
        from legacy_research.extensions.revenue.vectors.arbitrage import ArbitrageVector

        return ArbitrageVector
    if name == "OutreachVector":
        from legacy_research.extensions.revenue.vectors.outreach import OutreachVector

        return OutreachVector
    raise AttributeError(f"module 'cortex.extensions.revenue.vectors' has no attribute {name!r}")
