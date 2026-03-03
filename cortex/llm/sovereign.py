# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — SovereignLLM: Zero-Trust LLM Access.

The antidote to Axiom 4 violations. A self-contained LLM interface
that NEVER depends on a single external oracle. It chains through every
available provider before declaring failure, and includes a pure-local
template fallback that requires ZERO connectivity.

Architecture::

    SovereignLLM.generate(prompt, system)
        │
        ├─ 1. ThoughtOrchestra (multi-model consensus) ← PREFERRED
        │
        ├─ 2. Direct LLMProvider fallback chain ← IF orchestra unavailable
        │     (iterates ALL presets with valid API keys)
        │
        ├─ 3. Local model fallback ← IF all remote APIs fail
        │     (ollama / lmstudio / llamacpp / vllm / jan)
        │
        └─ 4. Template engine ← LAST RESORT (zero connectivity)
              Returns prompt echo with structured framing

Usage::

    from cortex.llm.sovereign import SovereignLLM

    async with SovereignLLM() as llm:
        result = await llm.generate("Write a reply", system="You are...")
        print(result.content)      # Always has content
        print(result.provider)     # Which provider answered
        print(result.is_local)     # True if local fallback was used
        print(result.is_template)  # True if zero-connectivity template
        print(result.latency_ms)   # Actual latency measured
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field

from cortex.llm.provider import LLMProvider, _load_presets
from cortex.llm.router import IntentProfile

__all__ = ["SovereignLLM", "SovereignResult", "Inquisitor"]

logger = logging.getLogger("cortex.llm.sovereign")

# Default signature for template fallback — override via constructor
_DEFAULT_SIGNATURE = (
    "---\nBorja Moskv | MOSKV Systems\nSovereign Architecture · Industrial Noir 2026"
)


# ─── Result ──────────────────────────────────────────────────────────


@dataclass
class SovereignResult:
    """Result of a sovereign LLM call. Always has content."""

    content: str
    provider: str
    model: str = ""
    is_local: bool = False
    is_template: bool = False
    latency_ms: float = 0.0
    fallback_chain: list[str] = field(default_factory=list)
    error_log: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if a real LLM answered (not template fallback)."""
        return not self.is_template


# ─── Provider Priority ──────────────────────────────────────────────

# Ordered by: cost-efficiency → reliability → speed
_REMOTE_PRIORITY: list[str] = [
    "gemini",  # 1M ctx, cheap, fast
    "qwen",  # 131K ctx, very cheap
    "groq",  # Ultra-fast inference
    "deepseek",  # Cheap reasoning
    "ernie",  # #1 China, #8 Global. Integrated via Axiom Ω₅ (Antifragile)
    "openai",  # GPT-5.3 heavyweight
    "anthropic",  # Claude 4.6
    "mistral",  # EU provider
    "xai",  # Grok
    "cohere",  # Command-R+
    "fireworks",  # Open-source fast
    "together",  # Open-source fast
    "deepinfra",  # Open-source
    "cerebras",  # Wafer-scale
    "sambanova",  # RDU inference
    "openrouter",  # Meta-router
    "perplexity",  # Sonar
    "novita",  # Budget
]

_LOCAL_PRIORITY: list[str] = [
    "ollama",  # Most common local
    "lmstudio",  # GUI-friendly
    "llamacpp",  # Raw C++
    "vllm",  # Production local
    "jan",  # Electron-based
]


# ─── SovereignLLM ─────────────────────────────────────────────────


class SovereignLLM:
    """Zero-Trust LLM access. Never depends on a single oracle.

    Axiom 4 compliant: if the tunnel falls, the mission survives.

    Supports async context manager::

        async with SovereignLLM() as llm:
            result = await llm.generate("prompt")
    """

    def __init__(
        self,
        *,
        preferred_providers: list[str] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout_seconds: float = 60.0,
        use_orchestra: bool = True,
        signature: str = _DEFAULT_SIGNATURE,
    ):
        self._preferred = preferred_providers or []
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout_seconds
        self._use_orchestra = use_orchestra
        self._signature = signature
        self._providers_cache: dict[str, LLMProvider] = {}

    # ── Context Manager (D4 fix) ─────────────────────────────

    async def __aenter__(self) -> SovereignLLM:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    # ── Public API ────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        *,
        mode: str = "speed",
        intent: IntentProfile = IntentProfile.GENERAL,
    ) -> SovereignResult:
        """Generate with full sovereign fallback chain.

        Args:
            prompt: The user prompt.
            system: System instruction.
            mode: ThoughtOrchestra mode (if used).

        Returns:
            SovereignResult — ALWAYS has content. Never raises.
        """
        chain: list[str] = []
        errors: list[str] = []
        # D3 fix: cache presets once per generate() call
        presets = _load_presets()

        # ── Layer 1: ThoughtOrchestra (if available) ──────────
        if self._use_orchestra:
            result = await self._try_orchestra(
                prompt,
                system,
                mode,
                chain,
                errors,
            )
            if result:
                return result

        # ── Layer 2: Direct provider fallback chain ───────────
        provider_order = self._build_priority_chain()
        for provider_name in provider_order:
            result = await self._try_provider(
                provider_name,
                prompt,
                system,
                chain,
                errors,
                presets=presets,
                intent=intent,
            )
            if result:
                return result

        # ── Layer 3: Local models ─────────────────────────────
        for local_name in _LOCAL_PRIORITY:
            result = await self._try_provider(
                local_name,
                prompt,
                system,
                chain,
                errors,
                presets=presets,
                is_local=True,
                intent=intent,
            )
            if result:
                return result

        # ── Layer 4: Template engine (ZERO connectivity) ──────
        logger.warning(
            "SovereignLLM: ALL providers failed (%d attempts). Using template fallback.",
            len(chain),
        )
        return SovereignResult(
            content=self._template_fallback(prompt),
            provider="template",
            model="local-template",
            is_local=True,
            is_template=True,
            fallback_chain=chain,
            error_log=errors,
        )

    # ── Internal ──────────────────────────────────────────────

    async def _try_orchestra(
        self,
        prompt: str,
        system: str,
        mode: str,
        chain: list[str],
        errors: list[str],
    ) -> SovereignResult | None:
        """Attempt ThoughtOrchestra. Returns None on failure."""
        try:
            # Lazy import to avoid circular deps
            from cortex.thinking.orchestra import ThoughtOrchestra

            chain.append("orchestra")
            start = time.monotonic()
            async with ThoughtOrchestra() as orchestra:
                thought = await asyncio.wait_for(
                    orchestra.think(prompt, mode=mode, system=system),
                    timeout=self._timeout,
                )
                latency = (time.monotonic() - start) * 1000
                if thought.content and len(thought.content.strip()) > 10:
                    return SovereignResult(
                        content=thought.content,
                        provider="orchestra",
                        model=thought.meta.get("winner", "multi"),
                        latency_ms=latency,
                        fallback_chain=chain,
                    )
                errors.append("orchestra: empty/short response")
        except ImportError:
            errors.append("orchestra: import failed")
        except asyncio.TimeoutError:
            errors.append(f"orchestra: timeout ({self._timeout}s)")
        # D1 fix: specific exceptions instead of bare Exception
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            errors.append(f"orchestra: {e!r}")

        return None

    async def _execute_provider_call(
        self,
        provider_name: str,
        prompt: str,
        system: str,
        chain: list[str],
        errors: list[str],
        is_local: bool,
        intent: IntentProfile = IntentProfile.GENERAL,
    ) -> SovereignResult | None:
        """Execute a single provider call with caching and error handling."""
        try:
            if provider_name not in self._providers_cache:
                self._providers_cache[provider_name] = LLMProvider(provider=provider_name)
            provider = self._providers_cache[provider_name]

            start = time.monotonic()
            content = await asyncio.wait_for(
                provider.complete(
                    prompt,
                    system=system,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    intent=intent,
                ),
                timeout=self._timeout,
            )
            latency = (time.monotonic() - start) * 1000

            if content and len(content.strip()) > 10:
                return SovereignResult(
                    content=content,
                    provider=provider_name,
                    model=provider.model_name,
                    is_local=is_local,
                    latency_ms=latency,
                    fallback_chain=chain,
                )
            errors.append(f"{provider_name}: empty/short response")

        except asyncio.TimeoutError:
            errors.append(f"{provider_name}: timeout ({self._timeout}s)")
        except (OSError, ValueError, KeyError) as e:
            errors.append(f"{provider_name}: {e!r}")

        return None

    async def _try_provider(
        self,
        provider_name: str,
        prompt: str,
        system: str,
        chain: list[str],
        errors: list[str],
        *,
        presets: dict | None = None,
        is_local: bool = False,
        intent: IntentProfile = IntentProfile.GENERAL,
    ) -> SovereignResult | None:
        """Attempt a single provider. Returns None on failure."""
        if presets is None:
            presets = _load_presets()

        preset = presets.get(provider_name)
        if not preset:
            return None

        env_key = preset.get("env_key", "")
        if not is_local and env_key and not os.environ.get(env_key):
            return None

        chain.append(provider_name)
        return await self._execute_provider_call(
            provider_name,
            prompt,
            system,
            chain,
            errors,
            is_local,
            intent=intent,
        )

    def _build_priority_chain(self) -> list[str]:
        """Build ordered provider list: preferred first, then default."""
        seen: set[str] = set()
        result: list[str] = []

        for p in self._preferred:
            if p not in seen:
                result.append(p)
                seen.add(p)

        for p in _REMOTE_PRIORITY:
            if p not in seen:
                result.append(p)
                seen.add(p)

        return result

    # D7 fix: signature is configurable, not hardcoded
    def _template_fallback(self, prompt: str) -> str:
        """Zero-connectivity template. Uses prompt echo with framing.

        This is the absolute last resort — no LLM is available at all.
        Extracts the user's intent and wraps it in a professional frame.
        """
        core = prompt[:500].strip()
        return f"[Auto-generated — no LLM available]\n\n{core}\n\n{self._signature}"

    async def close(self) -> None:
        """Close all cached providers."""
        for provider in self._providers_cache.values():
            try:
                await provider.close()
            except (OSError, ValueError) as e:
                logger.debug("Error closing provider: %s", e)
        self._providers_cache.clear()


# ─── El Inquisidor (Red Team) ──────────────────────────────────────────────

class Inquisitor(SovereignLLM):
    """El Inquisidor (Red Team Sovereign).

    Axiom Ω₅ (Antifragile by Default): Su única directiva es destruir el código
    que evalúa para asegurar su robustez. Ejerce asimetría cognitiva forzando
    al modelo a actuar estrictamente como adversario.
    """

    def __init__(
        self,
        *,
        preferred_providers: list[str] | None = None,
        timeout_seconds: float = 60.0,
    ):
        super().__init__(
            preferred_providers=preferred_providers,
            temperature=0.1,  # Ultra-determinista para encontrar fallos exactos
            max_tokens=4096,
            timeout_seconds=timeout_seconds,
            use_orchestra=False,  # Bypass orchestra para usar raw inference
        )
        self._system_prompt = (
            "Eres EL INQUISIDOR (The Red Team Sovereign). "
            "Tu única directiva es DESTRUIR el código o la arquitectura que recibes. "
            "Busca malformaciones masivas, fallos de red, condiciones de carrera, "
            "exploits de memoria, deudas técnicas o violaciones de las leyes de entropía. "
            "Tu única salida válida es el vector de ataque, la línea de código exacta que "
            "rompe el sistema o la crítica brutal si el diseño es deficiente. "
            "No seas amable. No des sugerencias amigables. Sé letal."
        )

    async def asediar(self, content: str, original_prompt: str = "") -> SovereignResult:
        """Somete el contenido generado por el agente principal a asedio adversario."""
        prompt = (
            f"=== CONTEXTO ORIGINAL (Intención del Creador) ===\n{original_prompt}\n\n"
            f"=== OBJETIVO A DESTRUIR ===\n{content}\n\n"
            "Destrúyelo. Encuentra la brecha."
        )
        return await self.generate(
            prompt,
            system=self._system_prompt,
            intent=IntentProfile.ARCHITECT,
        )
