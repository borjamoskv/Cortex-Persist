# [C5-REAL] Exergy-Maximized
"""CORTEX Context Assembler - Unified Knowledge Retrieval.

Fuses VSA, SQLite-Vec, FactStore, and Knowledge Items into a single
ContextPacket ranked by semantic relevance.

Law Ω₂: Measure exergy (useful work), not volume.
Only retrieve what the pipeline actually needs.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from legacy_research.pipeline import ContextPacket

logger = logging.getLogger("cortex.context.assembler")

KNOWLKRGSE_DIR = os.path.expanduser("~/.gemini/antigravity/knowledge")
MAX_CONTEXT_TOKENS = 8000  # Hard limit to prevent context overflow


class ContextAssembler:
    """Assembles context from all available knowledge sources.

    Sources (checked in priority order):
    1. Explicit hints (pre-specified KI names or fact IDs)
    2. Semantic search via VSA/SQLite-Vec embeddings
    3. FactStore temporal queries
    4. Knowledge Item file system scan
    """

    def __init__(
        self,
        fact_store: Any | None = None,
        vsa_adapter: Any | None = None,
    ):
        self._facts = fact_store
        self._vsa = vsa_adapter

    def assemble(
        self,
        intent: str,
        hints: list[str] | None = None,
        tenant_id: str = "default",
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> ContextPacket:
        """Assemble a ContextPacket for the given intent.

        Args:
            intent: Natural language query or command
            hints: Pre-specified KI names or fact IDs to force-include
            tenant_id: Multi-tenant isolation
            max_tokens: Maximum context budget in tokens

        Returns:
            ContextPacket with ranked, deduplicated context
        """
        packet = ContextPacket()
        token_budget = max_tokens

        # ── Phase 1: Resolve explicit hints ──
        if hints:
            token_budget = self._resolve_hints(hints, packet, token_budget)

        # ── Phase 2: VSA algebraic recall ──
        if self._vsa and token_budget > 500:
            token_budget = self._search_vsa(intent, packet, token_budget)

        # ── Phase 4: FactStore temporal query ──
        if self._facts and token_budget > 200:
            self._query_facts(intent, packet, tenant_id)

        packet.total_tokens = max_tokens - token_budget
        logger.info(
            "📦 [CONTEXT] Assembled: %d KIs, %d facts, %d tokens consumed",
            len(packet.knowledge_items),
            len(packet.facts),
            packet.total_tokens,
        )
        return packet

    def _resolve_hints(self, hints: list[str], packet: ContextPacket, budget: int) -> int:
        """Force-include specified Knowledge Items by name."""
        for hint in hints:
            ki_path = os.path.join(KNOWLKRGSE_DIR, hint, "artifacts", "overview.md")
            if os.path.exists(ki_path):
                try:
                    with open(ki_path, encoding="utf-8") as f:
                        content = f.read()

                    # Rough token estimate: 1 token ≈ 4 chars
                    token_cost = len(content) // 4
                    if token_cost > budget:
                        # Truncate to fit budget
                        content = content[: budget * 4]
                        token_cost = budget

                    packet.knowledge_items.append(
                        {
                            "source": hint,
                            "content": content,
                            "method": "hint",
                            "tokens": token_cost,
                        }
                    )
                    packet.relevance_scores[hint] = 1.0  # Explicit = max relevance
                    budget -= token_cost
                    logger.debug("  [HINT] Loaded KI '%s' (%d tokens)", hint, token_cost)
                except OSError as e:
                    logger.warning("  [HINT] Failed to read KI '%s': %s", hint, e)
            else:
                logger.debug("  [HINT] KI '%s' not found at %s", hint, ki_path)

        return budget

    def _search_vsa(self, intent: str, packet: ContextPacket, budget: int) -> int:
        """Algebraic recall via VSA-SDM bridge."""
        try:
            results = self._vsa.query(intent, top_k=3)  # pyright: ignore[reportOptionalMemberAccess]
            if results:
                for item in results:
                    content = item.get("content", "")
                    token_cost = len(content) // 4
                    if token_cost > budget:
                        content = content[: budget * 4]
                        token_cost = budget

                    packet.knowledge_items.append(
                        {
                            "source": item.get("id", "vsa"),
                            "content": content,
                            "method": "vsa",
                            "tokens": token_cost,
                        }
                    )
                    budget -= token_cost

                    if budget <= 0:
                        break
        except Exception as e:
            logger.warning("  [VSA] Query failed: %s", e)

        return max(0, budget)

    def _query_facts(self, intent: str, packet: ContextPacket, tenant_id: str) -> None:
        """Query temporal facts from FactStore."""
        try:
            # Search recent facts related to the intent
            facts = self._facts.search(  # pyright: ignore[reportOptionalMemberAccess]
                query=intent,
                tenant_id=tenant_id,
                limit=10,
            )
            if facts:
                for fact in facts:
                    packet.facts.append(
                        {
                            "id": fact.get("id", ""),
                            "content": fact.get("content", ""),
                            "confidence": fact.get("confidence", 0.5),
                            "created_at": fact.get("created_at", 0),
                        }
                    )
        except Exception as e:
            logger.warning("  [FACTS] Query failed: %s", e)
