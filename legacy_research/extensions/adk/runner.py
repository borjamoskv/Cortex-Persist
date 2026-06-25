# [C5-REAL] Exergy-Maximized
"""CORTEX ADK Runner - CLI and Web interface for ADK agents.

Re-exports from legacy_research.adk.runner to avoid code duplication.
"""

from legacy_research.adk.runner import main, run_cli, run_web

__all__ = ["main", "run_cli", "run_web"]
