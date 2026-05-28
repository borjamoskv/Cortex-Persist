"""CORTEX v5.0 — Langbase Integration.

Serverless AI agents backed by CORTEX sovereign memory.
Opt-in: requires LANGBASE_API_KEY environment variable.
"""

from cortex.extensions.langbase.client import LangbaseClient

__all__ = ["LangbaseClient"]
