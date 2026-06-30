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
from pathlib import Path
from typing import Any

from babylon60.pipeline import ContextPacket

logger = logging.getLogger("babylon60.context.assembler")

KNOWLEDGE_DIR = os.environ.get(
    "CORTEX_KNOWLEDGE_DIR", os.path.expanduser("~/.gemini/antigravity/knowledge")
)
MAX_CONTEXT_TOKENS = 8000  # Hard limit to prevent context overflow


import asyncio


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
        knowledge_dir: str | Path | None = None,
    ):
        self._facts = fact_store
        self._vsa = vsa_adapter
        self._knowledge_dir = str(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR

    def _add_knowledge_item(
        self,
        packet: ContextPacket,
        source: str,
        content: str,
        method: str,
        token_cost: int,
        relevance: float,
    ) -> bool:
        """Helper to add knowledge item with content deduplication and budget tracking."""
        for existing in packet.knowledge_items:
            if existing["source"] == source:
                return False
            if len(existing["content"]) == len(content) and existing["content"] == content:
                return False

        packet.knowledge_items.append(
            {
                "source": source,
                "content": content,
                "method": method,
                "tokens": token_cost,
            }
        )
        packet.relevance_scores[source] = relevance
        return True

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

        # ── Phase 3: Knowledge Item file system scan ──
        if token_budget > 300:
            token_budget = self._scan_knowledge_dir(intent, packet, token_budget)

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

    async def assemble_async(
        self,
        intent: str,
        hints: list[str] | None = None,
        tenant_id: str = "default",
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> ContextPacket:
        """Assemble a ContextPacket for the given intent asynchronously.

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
            token_budget = await self._search_vsa_async(intent, packet, token_budget)

        # ── Phase 3: Knowledge Item file system scan ──
        if token_budget > 300:
            loop = asyncio.get_running_loop()
            token_budget = await loop.run_in_executor(
                None, lambda: self._scan_knowledge_dir(intent, packet, token_budget)
            )

        # ── Phase 4: FactStore temporal query ──
        if self._facts and token_budget > 200:
            await self._query_facts_async(intent, packet, tenant_id)

        packet.total_tokens = max_tokens - token_budget
        logger.info(
            "📦 [CONTEXT] Assembled Asynchronously: %d KIs, %d facts, %d tokens consumed",
            len(packet.knowledge_items),
            len(packet.facts),
            packet.total_tokens,
        )
        return packet

    def _scan_knowledge_dir(self, intent: str, packet: ContextPacket, budget: int) -> int:
        """Scan the local self._knowledge_dir for relevant files matching query terms."""
        if not os.path.exists(self._knowledge_dir) or budget <= 100:
            return budget

        try:
            # Tokenize intent into lowercase keywords for simple scanning
            query_terms = [t.lower() for t in intent.split() if len(t) > 3]
            if not query_terms:
                return budget

            # Scan files recursively
            for root, _, files in os.walk(self._knowledge_dir):
                for file in files:
                    if file.endswith(".md") or file.endswith(".txt"):
                        path = os.path.join(root, file)
                        path_lower = path.lower()
                        match_count = sum(1 for term in query_terms if term in path_lower)

                        if match_count > 0:
                            try:
                                with open(path, encoding="utf-8") as f:
                                    content = f.read()

                                # Score: 0.5 base + 0.1 per name match + content match boost
                                content_lower = content.lower()
                                content_match = sum(
                                    1 for term in query_terms if term in content_lower
                                )
                                relevance = (
                                    0.5 + (0.1 * match_count) + min(0.3, 0.05 * content_match)
                                )

                                token_cost = len(content) // 4
                                if token_cost > budget:
                                    content = content[: budget * 4]
                                    token_cost = budget

                                relative_name = os.path.relpath(path, self._knowledge_dir)

                                if self._add_knowledge_item(
                                    packet, relative_name, content, "fs_scan", token_cost, relevance
                                ):
                                    budget -= token_cost
                                    logger.debug(
                                        "  [FS_SCAN] Loaded KI '%s' (%d tokens, relevance %.2f)",
                                        relative_name,
                                        token_cost,
                                        relevance,
                                    )

                                if budget <= 0:
                                    return 0
                            except OSError:
                                continue
        except Exception as e:  # noqa: BLE001
            logger.warning("  [FS_SCAN] Scan failed: %s", e)

        return budget

    def _resolve_hints(self, hints: list[str], packet: ContextPacket, budget: int) -> int:
        """Force-include specified Knowledge Items by name or path."""
        for hint in hints:
            if budget <= 0:
                break

            # Check multiple potential targets: absolute/relative files, or nested overview.md
            paths_to_check = [
                os.path.join(self._knowledge_dir, hint),
                os.path.join(self._knowledge_dir, hint, "artifacts", "overview.md"),
                hint if os.path.isabs(hint) else "",
            ]

            loaded = False
            for path in paths_to_check:
                if path and os.path.isfile(path):
                    try:
                        with open(path, encoding="utf-8") as f:
                            content = f.read()

                        token_cost = len(content) // 4
                        if token_cost > budget:
                            content = content[: budget * 4]
                            token_cost = budget

                        source_name = (
                            os.path.relpath(path, self._knowledge_dir)
                            if path.startswith(self._knowledge_dir)
                            else os.path.basename(path)
                        )

                        if self._add_knowledge_item(
                            packet, source_name, content, "hint", token_cost, 1.0
                        ):
                            budget -= token_cost
                            loaded = True
                            logger.debug(
                                "  [HINT] Loaded KI file '%s' (%d tokens)",
                                source_name,
                                token_cost,
                            )
                            break
                    except OSError as e:
                        logger.warning("  [HINT] Failed to read KI file '%s': %s", path, e)

            if not loaded:
                logger.debug("  [HINT] KI '%s' not found or failed to load", hint)

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

                    source_id = item.get("id", "vsa")
                    relevance = item.get("similarity", 0.8)

                    if self._add_knowledge_item(
                        packet, source_id, content, "vsa", token_cost, relevance
                    ):
                        budget -= token_cost

                    if budget <= 0:
                        break
        except Exception as e:  # noqa: BLE001
            logger.warning("  [VSA] Query failed: %s", e)

        return max(0, budget)

    async def _search_vsa_async(self, intent: str, packet: ContextPacket, budget: int) -> int:
        """Algebraic recall via VSA-SDM bridge asynchronously."""
        if not self._vsa:
            return budget
        try:
            if hasattr(self._vsa, "query_async"):
                results = await self._vsa.query_async(intent, top_k=3)
            else:
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(None, lambda: self._vsa.query(intent, top_k=3))

            if results:
                for item in results:
                    content = item.get("content", "")
                    token_cost = len(content) // 4
                    if token_cost > budget:
                        content = content[: budget * 4]
                        token_cost = budget

                    source_id = item.get("id", "vsa")
                    relevance = item.get("similarity", 0.8)

                    if self._add_knowledge_item(
                        packet, source_id, content, "vsa", token_cost, relevance
                    ):
                        budget -= token_cost

                    if budget <= 0:
                        break
        except Exception as e:  # noqa: BLE001
            logger.warning("  [VSA] Async query failed: %s", e)

        return max(0, budget)

    def _query_facts(self, intent: str, packet: ContextPacket, tenant_id: str) -> None:
        """Query temporal facts from FactStore."""
        try:
            facts = None
            if hasattr(self._facts, "search_sync"):
                facts = self._facts.search_sync(query=intent, tenant_id=tenant_id, limit=10)
            elif hasattr(self._facts, "search"):
                facts = self._facts.search(query=intent, tenant_id=tenant_id, limit=10)

            if facts:
                for fact in facts:
                    fact_id = (
                        getattr(fact, "id", "")
                        if not isinstance(fact, dict)
                        else fact.get("id", "")
                    )
                    content = (
                        getattr(fact, "content", "")
                        if not isinstance(fact, dict)
                        else fact.get("content", "")
                    )
                    confidence = (
                        getattr(fact, "confidence", "C3")
                        if not isinstance(fact, dict)
                        else fact.get("confidence", "C3")
                    )
                    created_at = (
                        getattr(fact, "timestamp", 0)
                        if not isinstance(fact, dict)
                        else fact.get("timestamp", 0)
                    )
                    meta = (
                        getattr(fact, "metadata", {})
                        if not isinstance(fact, dict)
                        else fact.get("metadata", {})
                    )

                    if any(f["id"] == fact_id for f in packet.facts):
                        continue

                    packet.facts.append(
                        {
                            "id": fact_id,
                            "content": content,
                            "confidence": confidence,
                            "created_at": created_at,
                            "metadata": dict(meta) if meta else {},
                        }
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning("  [FACTS] Query failed: %s", e)

    async def _query_facts_async(self, intent: str, packet: ContextPacket, tenant_id: str) -> None:
        """Query temporal facts from FactStore asynchronously."""
        try:
            facts = None
            if hasattr(self._facts, "_search_async"):
                facts = await self._facts._search_async(intent, tenant_id=tenant_id, limit=10)
            elif hasattr(self._facts, "search"):
                res = self._facts.search(query=intent, tenant_id=tenant_id, limit=10)
                if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
                    facts = await res
                else:
                    facts = res

            if facts:
                for fact in facts:
                    fact_id = (
                        getattr(fact, "id", "")
                        if not isinstance(fact, dict)
                        else fact.get("id", "")
                    )
                    content = (
                        getattr(fact, "content", "")
                        if not isinstance(fact, dict)
                        else fact.get("content", "")
                    )
                    confidence = (
                        getattr(fact, "confidence", "C3")
                        if not isinstance(fact, dict)
                        else fact.get("confidence", "C3")
                    )
                    created_at = (
                        getattr(fact, "timestamp", 0)
                        if not isinstance(fact, dict)
                        else fact.get("timestamp", 0)
                    )
                    meta = (
                        getattr(fact, "metadata", {})
                        if not isinstance(fact, dict)
                        else fact.get("metadata", {})
                    )

                    if any(f["id"] == fact_id for f in packet.facts):
                        continue

                    packet.facts.append(
                        {
                            "id": fact_id,
                            "content": content,
                            "confidence": confidence,
                            "created_at": created_at,
                            "metadata": dict(meta) if meta else {},
                        }
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning("  [FACTS] Async query failed: %s", e)
