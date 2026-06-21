# [C5-REAL] Exergy-Maximized
"""CORTEX Level 3 Copilot - LLM-Backed Suggestion Strategy.

Production strategy that calls an actual LLM API for code completions.
Supports FIM (Fill-in-the-Middle) and standard completion modes.

The LLMClient protocol allows swapping backends: Gemini, OpenAI, local models.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import uuid4

from cortex.agents.builtins.copilot_agent import SuggestionStrategy
from cortex.agents.copilot_cache import SuggestionCache
from cortex.agents.copilot_context import (
    ContextWindow,
    build_context_window,
)
from cortex.agents.copilot_contracts import (
    Confidence,
    CopilotContextPayload,
    SuggestionBatch,
    SuggestionKind,
    SuggestionProposal,
)

logger = logging.getLogger("cortex.agents.copilot.llm_strategy")


# ── LLM Client Protocol ──────────────────────────────────────────


@dataclass
class LLMResponse:
    """Response from an LLM completion call."""

    text: str
    tokens_used: int
    model: str
    latency_ms: float
    finish_reason: str  # "stop", "length", "timeout", "error"


@runtime_checkable
class LLMClient(Protocol):
    """Abstract LLM client protocol. Swap implementations freely.

    Implementations:
        - GeminiClient (Google AI)
        - OpenAIClient (OpenAI / Azure)
        - LocalClient (Ollama, vLLM, llama.cpp)
    """

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a completion for the given prompt."""
        ...


# ── Deterministic Fallback Client ─────────────────────────────────


class DeterministicFallbackClient:
    """Fallback client when no LLM is available or API fails.

    Returns simple pattern-based completions. NOT a real LLM -
    used only as a degraded fallback.
    """

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        t0 = time.monotonic()

        # Simple pattern detection for fallback completions
        text = ""
        if prompt.rstrip().endswith(":"):
            text = "\n    pass\n"
        elif "def " in prompt and '"""' not in prompt:
            text = '    """PENDING: Add documentation."""\n'
        elif "class " in prompt and "pass" not in prompt:
            text = "\n    def __init__(self):\n        pass\n"
        elif prompt.rstrip().endswith(","):
            text = "\n"

        latency = (time.monotonic() - t0) * 1000

        return LLMResponse(
            text=text,
            tokens_used=len(text) // 4,
            model="deterministic-fallback",
            latency_ms=latency,
            finish_reason="stop",
        )


# ── LLM Completion Strategy ──────────────────────────────────────


class LLMCompletionStrategy(SuggestionStrategy):
    """Production strategy that calls an LLM API for code completions.

    Features:
        - Uses ContextWindow for intelligent prefix/suffix truncation
        - Supports FIM (fill-in-the-middle) mode for compatible models
        - Caches results via SuggestionCache
        - Falls back to deterministic completions on API failure
        - Enforces token budget and timeout

    Architecture (Level 3 constraint):
        This strategy ONLY generates suggestions. It NEVER applies them.
        All results are SuggestionProposal objects awaiting human verdict.
    """

    def __init__(
        self,
        client: LLMClient,
        *,
        cache: SuggestionCache | None = None,
        use_fim: bool = True,
        context_budget_tokens: int = 2048,
        max_completion_tokens: int = 256,
        timeout_seconds: float = 5.0,
        temperature: float = 0.0,
        num_completions: int = 1,
    ) -> None:
        self._client = client
        self._fallback = DeterministicFallbackClient()
        self._cache = cache
        self._use_fim = use_fim
        self._context_budget = context_budget_tokens
        self._max_completion_tokens = max_completion_tokens
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._num_completions = num_completions

    async def generate(
        self,
        context: CopilotContextPayload,
        *,
        model: str = "gemini-2.5-pro",
    ) -> list[SuggestionProposal]:
        """Generate LLM-backed code completions.

        Flow:
            1. Check cache → return if hit
            2. Build context window (smart truncation)
            3. Format prompt (FIM or standard)
            4. Call LLM API with timeout
            5. Parse response → SuggestionProposal
            6. Cache result
            7. Fallback on any error

        Args:
            context: Editor context from IDE.
            model: LLM model identifier.

        Returns:
            List of SuggestionProposals (NEVER applied, only proposed).
        """
        from cortex.agents.builtins.copilot_agent import _hash_context

        context_hash = _hash_context(context)

        # 1. Check cache
        if self._cache is not None:
            cached = self._cache.get(context_hash)
            if cached is not None:
                logger.debug(
                    "Cache hit for %s, returning %d cached suggestions",
                    context_hash,
                    len(cached.suggestions),
                )
                return cached.suggestions

        # 2. Build context window
        window = build_context_window(
            context.cursor.prefix,
            context.cursor.suffix,
            budget_tokens=self._context_budget,
            language=context.cursor.language,
        )

        # 3. Format prompt
        prompt = self._format_prompt(window, model)

        # 4. Call LLM API with timeout + fallback
        proposals: list[SuggestionProposal] = []

        for _i in range(self._num_completions):
            try:
                response = await self._call_with_timeout(
                    prompt,
                    model=model,
                )
                proposal = self._response_to_proposal(response, context_hash, window)
                proposals.append(proposal)

            except TimeoutError:
                logger.warning("LLM timeout after %.1fs, using fallback", self._timeout)
                fallback_response = await self._fallback.complete(
                    prompt, max_tokens=self._max_completion_tokens
                )
                proposals.append(
                    self._response_to_proposal(fallback_response, context_hash, window)
                )

            except Exception as exc:
                logger.error("LLM call failed: %s, using fallback", exc)
                fallback_response = await self._fallback.complete(
                    prompt, max_tokens=self._max_completion_tokens
                )
                proposals.append(
                    self._response_to_proposal(fallback_response, context_hash, window)
                )

        # 5. Cache the result
        if self._cache is not None and proposals:
            batch = SuggestionBatch(
                suggestions=proposals,
                context_hash=context_hash,
            )
            self._cache.put(
                context_hash,
                batch,
                file_paths=[context.cursor.file_path],
            )

        return proposals[: context.max_suggestions]

    # ── Prompt Formatting ─────────────────────────────────────────

    def _format_prompt(self, window: ContextWindow, model: str) -> str:
        """Format the prompt using FIM or standard mode."""
        if self._use_fim and self._model_supports_fim(model):
            # FIM format: <prefix>...<suffix>...<middle>
            return f"{window.fim_prefix}{window.fim_suffix}{window.fim_middle}"
        # Standard completion: just the prefix
        return window.prefix

    @staticmethod
    def _model_supports_fim(model: str) -> bool:
        """Check if a model supports fill-in-the-middle."""
        fim_models = {
            "codestral",
            "deepseek-coder",
            "starcoder",
            "code-llama",
            "qwen-coder",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
        }
        model_lower = model.lower()
        return any(fm in model_lower for fm in fim_models)

    # ── LLM Call ──────────────────────────────────────────────────

    async def _call_with_timeout(
        self,
        prompt: str,
        *,
        model: str,
    ) -> LLMResponse:
        """Call the LLM client with a timeout."""
        import asyncio

        stop_tokens = ["\n\n", "\ndef ", "\nclass ", "\n#"]

        try:
            result = await asyncio.wait_for(
                self._client.complete(
                    prompt,
                    max_tokens=self._max_completion_tokens,
                    temperature=self._temperature,
                    stop=stop_tokens,
                ),
                timeout=self._timeout,
            )
            return result
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"LLM call timed out after {self._timeout}s") from exc

    # ── Response Parsing ──────────────────────────────────────────

    def _response_to_proposal(
        self,
        response: LLMResponse,
        context_hash: str,
        window: ContextWindow,
    ) -> SuggestionProposal:
        """Convert an LLM response to a SuggestionProposal."""
        # Determine confidence based on finish reason and length
        if response.finish_reason == "error":
            confidence = Confidence.LOW
        elif response.finish_reason == "length":
            confidence = Confidence.MEDIUM
        elif response.tokens_used > 10:
            confidence = Confidence.HIGH
        else:
            confidence = Confidence.MEDIUM

        return SuggestionProposal(
            suggestion_id=f"llm-{uuid4().hex[:12]}",
            kind=SuggestionKind.CODE_COMPLETION,
            confidence=confidence,
            inline_text=response.text,
            explanation=f"LLM completion ({response.model}, {response.tokens_used} tokens)",
            source_context_hash=context_hash,
            model_used=response.model,
            tokens_consumed=response.tokens_used,
        )
