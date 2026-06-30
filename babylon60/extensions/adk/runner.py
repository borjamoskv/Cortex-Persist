# [C5-REAL] Exergy-Maximized
"""CORTEX ADK Runner - CLI and Web interface for ADK agents.

Re-exports from babylon60.adk.runner to avoid code duplication.
"""

from babylon60.adk.runner import main, run_cli, run_web

__all__ = ["main", "run_cli", "run_web"]
