# [C5-REAL] Exergy-Maximized

from __future__ import annotations

from typing import TYPE_CHECKING

from cortex_extensions.llm._cascade import classify_tier
from cortex_extensions.llm._models import CascadeTier, IntentProfile, ReasoningMode

if TYPE_CHECKING:
    from cortex_extensions.llm._cascade import CascadeManager
    from cortex_extensions.llm._models import BaseProvider, CortexPrompt

# Cost class ordering for tiebreaking (cheaper first)
COST_ORDER: dict[str, int] = {
    "free": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "variable": 4,
}

# Tier ordering (higher quality first)
TIER_ORDER: dict[str, int] = {
    "frontier": 0,
    "high": 1,
    "local": 2,
}


def promote_by_latency_then_cost(
    cascade: CascadeManager,
    providers: list[BaseProvider],
    intent: IntentProfile,
    estimated_tokens: int = 0,
    requires_frontier: bool = False,
) -> list[BaseProvider]:
    """A-record first (by latency), unknowns by (cost, tier)."""
    from cortex.config import LLM_LOCAL_FIRST

    fits_context: list[BaseProvider] = []
    overflows_context: list[BaseProvider] = []
    for p in providers:
        p_window = getattr(p, "context_window", 128000)
        if p_window and estimated_tokens > p_window:
            overflows_context.append(p)
        else:
            fits_context.append(p)

    def process_group(group: list[BaseProvider]) -> list[BaseProvider]:
        if not group:
            return []
        p_known = cascade.promote_known_good(group, intent)
        known_count = sum(1 for p in p_known if cascade.get_a_record(p.provider_name))
        known = p_known[:known_count]
        unknown = p_known[known_count:]

        tier_order = TIER_ORDER.copy()
        if LLM_LOCAL_FIRST:
            tier_order["local"] = -1

        if requires_frontier:
            unknown.sort(
                key=lambda p: (
                    p.tier != "frontier",
                    COST_ORDER.get(p.cost_class, 4),
                    tier_order.get(p.tier, 2),
                )
            )
        else:
            unknown.sort(
                key=lambda p: (
                    COST_ORDER.get(p.cost_class, 4),
                    tier_order.get(p.tier, 2),
                )
            )
        return known + unknown

    return process_group(fits_context) + process_group(overflows_context)


def ordered_fallbacks(
    cascade: CascadeManager,
    fallbacks: list[BaseProvider],
    prompt: CortexPrompt | IntentProfile,
) -> list[BaseProvider]:
    """Ordena fallbacks: intent affinity → A-record → cost → tier."""
    if isinstance(prompt, IntentProfile):
        effective_intent = prompt
        reasoning_mode = None
        estimated_tokens = 0
        requires_frontier_coercion = False
    else:
        effective_intent = prompt.intent
        reasoning_mode = prompt.reasoning_mode

        system_instruction = getattr(prompt, "system_instruction", "") or ""
        working_memory = getattr(prompt, "working_memory", []) or []
        total_chars = len(system_instruction)
        for msg in working_memory:
            if isinstance(msg, dict) and "content" in msg:
                total_chars += len(str(msg["content"]))
        estimated_tokens = (total_chars // 3) + (getattr(prompt, "max_tokens", 0) or 0)

        prompt_text = system_instruction.lower()
        for msg in working_memory:
            if isinstance(msg, dict) and "content" in msg:
                prompt_text += " " + str(msg["content"]).lower()
        requires_frontier_coercion = any(
            term in prompt_text for term in ["anvil", "z3", "formal", "verify"]
        )

    if reasoning_mode in (
        ReasoningMode.DEEP_THINK,
        ReasoningMode.ULTRA_THINK,
        ReasoningMode.DEEP_RESEARCH,
    ):
        effective_intent = IntentProfile.REASONING

    typed_matches: list[BaseProvider] = []
    safety_net: list[BaseProvider] = []

    for p in fallbacks:
        if classify_tier(p, effective_intent) == CascadeTier.TYPED_MATCH:
            typed_matches.append(p)
        else:
            safety_net.append(p)

    if reasoning_mode == ReasoningMode.ULTRA_THINK:
        frontier_typed = [p for p in typed_matches if p.tier == "frontier"]
        frontier_safety = [p for p in safety_net if p.tier == "frontier"]
        if frontier_typed or frontier_safety:
            typed_matches = frontier_typed
            safety_net = frontier_safety

    promoted_typed = promote_by_latency_then_cost(
        cascade, typed_matches, effective_intent, estimated_tokens, requires_frontier_coercion
    )
    promoted_safety = promote_by_latency_then_cost(
        cascade, safety_net, effective_intent, estimated_tokens, requires_frontier_coercion
    )

    return promoted_typed + promoted_safety
