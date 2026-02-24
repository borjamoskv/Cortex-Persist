# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v6.0 — Context Fusion Engine.

Distilla hechos crudos recuperados de L2 en contexto de alta densidad.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("cortex.thinking.context_fusion")


class ContextFusion:
    """Motor de Fusión Semántica de Contexto para RAG (CORTEX v6).

    Intercepts raw recalled facts from L2 and synthesizes them into actionable
    context before the main LLM processes the user prompt, eliminating context bloat.
    """

    SYNTHESIS_SYSTEM = (
        "You are MOSKV-1 (Identity: The Sovereign Architect). "
        "You are a memory distillation engine. "
        "Review the retrieved historical facts in the context of the latest user prompt. "
        "Your job is to:\n"
        "1. Extract ONLY the facts strictly relevant to answering the prompt.\n"
        "2. Resolve contradictions (prioritize Diamond facts and recent ones).\n"
        "3. Output a single, coherent 'Distilled Context' block.\n"
        "Output ONLY the actionable distilled context. No meta-commentary."
    )

    JUDGE_MAX_RETRIES = 2
    JUDGE_TIMEOUT_S = 8.0
    JUDGE_BACKOFF_BASE = 0.5

    def __init__(self, judge_provider=None):
        """Initializes ContextFusion. `judge_provider` should be a fast model like Flash."""
        self._judge = judge_provider

    async def _judge_safe(self, prompt: str, system: str, **kwargs) -> str | None:
        """Llama al juez rápido con retries + timeout."""
        if self._judge is None:
            return None
        for attempt in range(self.JUDGE_MAX_RETRIES + 1):
            try:
                if not hasattr(self._judge, "complete"):
                    logger.error("ContextFusion: Judge provider lacks 'complete' method.")
                    return None
                return await asyncio.wait_for(
                    self._judge.complete(prompt=prompt, system=system, **kwargs),
                    timeout=self.JUDGE_TIMEOUT_S,
                )
            except (OSError, RuntimeError, asyncio.TimeoutError, AttributeError) as e:
                logger.warning(
                    "ContextFusion error (attempt %d/%d): %s",
                    attempt + 1,
                    self.JUDGE_MAX_RETRIES + 1,
                    e,
                )
            if attempt < self.JUDGE_MAX_RETRIES:
                await asyncio.sleep(self.JUDGE_BACKOFF_BASE * (2**attempt))
        return None

    async def fuse_context(self, user_prompt: str, retrieved_facts: list[dict[str, Any]]) -> str:
        """Sintetiza hechos crudos en un único bloque de contexto de alta densidad."""
        if not retrieved_facts:
            return ""

        # Fallback to direct string concatenation if no judge is available
        if not self._judge:
            return "\n".join(f.get("content", "") for f in retrieved_facts)

        parts = [
            f"--- FACT {i + 1} (score: {f.get('score', 0):.2f}) ---\n{f.get('content', '')}"
            for i, f in enumerate(retrieved_facts)
        ]
        judge_prompt = (
            f"LATEST USER PROMPT:\n{user_prompt}\n\nRAW RETRIEVED FACTS:\n" + "\n\n".join(parts)
        )
        synthesized = await self._judge_safe(
            prompt=judge_prompt,
            system=self.SYNTHESIS_SYSTEM,
            temperature=0.0,
            max_tokens=2048,
        )
        if not synthesized:
            logger.warning("ContextFusion failed, degrading to raw concatenation")
            return "\n".join(f.get("content", "") for f in retrieved_facts)
        return synthesized
