"""CORTEX v5.0 — LLM Provider Module.

OpenAI-compatible LLM integration for context-aware retrieval.
Supports Qwen (DashScope), OpenRouter, Ollama, and OpenAI.
"""
from __future__ import annotations
from typing import Any, Optional, Union, Tuple, List, Dict, Callable


from cortex.extensions.llm.manager import LLMManager
from cortex.extensions.llm.provider import LLMProvider

__all__ = ["LLMProvider", "LLMManager"]
