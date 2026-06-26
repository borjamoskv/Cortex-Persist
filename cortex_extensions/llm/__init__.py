# [C5-REAL] Exergy-Maximized
"""LLM Provider Module.

OpenAI-compatible LLM integration for context-aware retrieval.
Supports Qwen (DashScope), OpenRouter, Ollama, and OpenAI.
"""

from __future__ import annotations

from cortex_extensions.llm.manager import LLMManager
from cortex_extensions.llm.provider import LLMProvider

__all__ = ["LLMManager", "LLMProvider"]
