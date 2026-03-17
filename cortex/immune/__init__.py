"""Immune Module — Metastability detection and system health probes."""

from cortex.immune.probe import (
    MetastabilityReport,
    probe_metastability,
    probe_untested_assumptions,
)

__all__ = [
    "MetastabilityReport",
    "probe_metastability",
    "probe_untested_assumptions",
]
