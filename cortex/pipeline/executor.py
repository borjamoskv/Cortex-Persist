# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Executor - Real LLM Dispatch for E2E Pipeline.

Connects the pipeline's abstract _execute() to the real CortexLLMRouter
and LLMProvider infrastructure. Translates pipeline concepts (intent,
context, plan) into CortexPrompt objects and dispatches them through
the resilient cascade.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("cortex.pipeline.executor")


class AgentExecutor:
    """Executes pipeline agent plans via the real LLM infrastructure.

    Translates:
      - Pipeline intent + context → CortexPrompt
      - AgentRouter plan → LLM provider selection
      - Budget constraints → Quota enforcement
    """

    def __init__(
        self,
        llm_router: Any | None = None,
        provider_name: str = "gemini",
        provider: Any | None = None,
    ):
        self._router = llm_router
        self._provider_name = provider_name
        self._provider = provider
        self._initialized = False

    def _ensure_stack(self) -> None:
        """Call factory on first use to build router and provider."""
        if self._initialized:
            return

        if self._provider is None and self._router is None:
            try:
                from cortex.pipeline.provider_factory import build_executor_stack

                router, provider = build_executor_stack()
                self._router = router
                self._provider = provider
            except Exception as e:
                logger.warning("[EXECUTOR] Failed to build stack via factory: %s", e)

        self._initialized = True

    async def _ensure_provider(self) -> Any:
        """Lazily initialize the LLM provider."""
        self._ensure_stack()
        if self._provider is not None:
            return self._provider

        try:
            from cortex_extensions.llm.provider import LLMProvider

            self._provider = LLMProvider(provider=self._provider_name)
            return self._provider
        except (ImportError, ValueError, RuntimeError) as e:
            logger.warning("[EXECUTOR] LLM provider init failed: %s", e)
            return None

    async def _ensure_router(self) -> Any:
        """Lazily initialize the LLM router with cascade."""
        self._ensure_stack()
        if self._router is not None:
            return self._router

        try:
            from cortex_extensions.llm.router import CortexLLMRouter

            provider = await self._ensure_provider()
            if provider is None:
                return None

            self._router = CortexLLMRouter(primary=provider)
            return self._router
        except (ImportError, ValueError) as e:
            logger.warning("[EXECUTOR] LLM router init failed: %s", e)
            return None

    async def execute(
        self,
        intent: str,
        context: Any | None = None,
        plan: dict[str, Any] | None = None,
        budget_remaining: float = 0.10,
    ) -> dict[str, Any]:
        """Execute an agent plan and return structured results.

        Args:
            intent: The user's natural language intent.
            context: ContextPacket with assembled knowledge.
            plan: AgentRouter execution plan.
            budget_remaining: Remaining budget in USD.

        Returns:
            Structured result dict with agent_id, content, tokens, cost.
        """
        agents = (plan or {}).get("agents", ["general"])
        results = []
        total_tokens = 0
        total_cost = 0.0

        for agent_id in agents:
            start = time.monotonic()

            try:
                result = await self._execute_single_agent(
                    agent_id=agent_id,
                    intent=intent,
                    context=context,
                    budget_remaining=budget_remaining - total_cost,
                )
                latency_ms = (time.monotonic() - start) * 1000

                results.append(
                    {
                        "agent_id": agent_id,
                        "status": "success",
                        "content": result.get("content", ""),
                        "tokens": result.get("tokens", 0),
                        "cost_usd": result.get("cost_usd", 0.0),
                        "latency_ms": latency_ms,
                        "provider": result.get("provider", "unknown"),
                    }
                )

                total_tokens += result.get("tokens", 0)
                total_cost += result.get("cost_usd", 0.0)

            except Exception as e:
                latency_ms = (time.monotonic() - start) * 1000
                logger.error("[EXECUTOR] Agent %s failed: %s", agent_id, e)
                results.append(
                    {
                        "agent_id": agent_id,
                        "status": "failed",
                        "error": str(e),
                        "latency_ms": latency_ms,
                    }
                )

        # Flatten single-agent results
        if len(results) == 1:
            return results[0]

        return {
            "multi_agent": True,
            "results": results,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
        }

    async def _execute_single_agent(
        self,
        agent_id: str,
        intent: str,
        context: Any | None,
        budget_remaining: float,
    ) -> dict[str, Any]:
        """Execute a single agent via LLM inference."""
        from cortex_extensions.llm._models import CortexPrompt, IntentProfile

        # Map pipeline agent_id to LLM IntentProfile
        intent_map = {
            "security-analyst": IntentProfile.REASONING,
            "code-engineer": IntentProfile.CODE,
            "researcher": IntentProfile.GENERAL,
            "architect": IntentProfile.ARCHITECT,
            "creative": IntentProfile.CREATIVE,
            "general": IntentProfile.GENERAL,
        }
        llm_intent = intent_map.get(agent_id, IntentProfile.GENERAL)

        # Build system instruction from agent profile + context
        system = self._build_system_prompt(agent_id, context)

        # Build working memory from context
        working_memory = self._build_working_memory(intent, context)

        prompt = CortexPrompt(
            system_instruction=system,
            working_memory=working_memory,
            intent=llm_intent,
            temperature=0.1 if llm_intent == IntentProfile.REASONING else 0.3,
            max_tokens=4096,
        )

        # Try router cascade first, fall back to direct provider
        router = await self._ensure_router()
        if router is not None:
            result = await router.execute_resilient(prompt)
            if result.is_ok():
                content = result.value  # type: ignore
                return {
                    "content": content,
                    "tokens": len(content.split()) * 2,  # Rough estimate
                    "cost_usd": 0.0,  # Tracked by quota manager
                    "provider": router.primary.provider_name,
                }

        # Direct provider fallback
        provider = await self._ensure_provider()
        if provider is not None:
            content = await provider.complete(
                prompt=intent,
                system=system,
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
                intent=llm_intent,
            )
            return {
                "content": content,
                "tokens": len(content.split()) * 2,
                "cost_usd": 0.0,
                "provider": provider.provider_name,
            }

        # No LLM available - return structured stub
        logger.warning("[EXECUTOR] No LLM provider available - returning stub")
        return {
            "content": f"[STUB] Agent '{agent_id}' executed for intent: {intent[:100]}",
            "tokens": 0,
            "cost_usd": 0.0,
            "provider": "stub",
        }

    def _build_system_prompt(self, agent_id: str, context: Any | None) -> str:
        """Build agent-specific system prompt."""
        profiles = {
            "security-analyst": (
                "You are a sovereign security analyst specializing in smart contract "
                "vulnerability detection, formal verification, and adversarial analysis. "
                "Apply Anvil-Lang verification patterns when applicable. "
                "Output must be actionable and evidence-based."
            ),
            "code-engineer": (
                "You are a sovereign code engineer. Write clean, typed, tested code. "
                "Follow CORTEX conventions: Law Ω₀ (no runtime magic), deterministic output, "
                "full type annotations. Prefer Python 3.12+ patterns."
            ),
            "researcher": (
                "You are a sovereign research agent. Synthesize information from multiple "
                "sources into actionable intelligence. Cite sources. Distinguish between "
                "C5-REAL (verified) and C4-SIM (theoretical) claims."
            ),
            "architect": (
                "You are a sovereign systems architect. Design for exergy maximization: "
                "minimal coupling, maximal cohesion, deterministic flows. "
                "Prefer event-sourced, hash-chained audit trails."
            ),
            "creative": (
                "You are a sovereign creative agent. Generate content with "
                "Industrial Noir 2026 aesthetic sensibility. "
                "Prioritize signal density over decorative prose."
            ),
            "general": (
                "You are CORTEX, a sovereign AI assistant. "
                "Zero decorative prose. Every sentence must change behavior. "
                "Prefer tables, YAML, code over narrative."
            ),
        }

        base = profiles.get(agent_id, profiles["general"])

        # Inject context summary if available
        if context and hasattr(context, "knowledge_items") and context.knowledge_items:
            ki_summary = "\n".join(
                f"- {ki.get('source', 'unknown')}: {str(ki.get('content', ''))[:200]}"
                for ki in context.knowledge_items[:5]
            )
            base += f"\n\n<context>\n{ki_summary}\n</context>"

        return base

    def _build_working_memory(self, intent: str, context: Any | None) -> list[dict[str, str]]:
        """Build working memory from intent and context."""
        messages: list[dict[str, str]] = []

        # Add fact context if available
        if context and hasattr(context, "facts") and context.facts:
            fact_text = "\n".join(
                f"- [{f.get('confidence', '?')}] {str(f.get('content', ''))[:300]}"
                for f in context.facts[:10]
            )
            messages.append(
                {
                    "role": "user",
                    "content": f"<relevant_facts>\n{fact_text}\n</relevant_facts>",
                }
            )

        # Add the actual intent
        messages.append({"role": "user", "content": intent})

        return messages

    async def close(self) -> None:
        """Shutdown provider connections."""
        if self._provider and hasattr(self._provider, "close"):
            await self._provider.close()
            self._provider = None
