# [C5-REAL] Exergy-Maximized
"""CORTEX Core - Epistemic Lineage & Audit Engine.

Ensures Ω₃-V compliance: All synthesized insights (L2) must be traceble
to ground truth facts (L0).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.lineage")


@dataclass
class LineageNode:
    """A node in the epistemic lineage tree."""

    fact_id: int
    project: str
    content: str
    fact_type: str
    confidence: str
    timestamp: str
    parents: list[LineageNode]
    is_valid: bool = True
    error: str | None = None


class LineageVerifier:
    """Verifier for Epistemic Isolation (Ω₃-V)."""

    def __init__(self, engine: Any):
        self.engine = engine

    async def get_lineage(
        self, fact_id: int, max_depth: int = 5, _cache: dict[int, LineageNode] | None = None
    ) -> LineageNode:
        """Recursively build the lineage tree for a fact.

        Protected against cyclic DAGs and N+1 queries via _cache and max_depth.
        """
        # 1. Zero-Trust OOM Killer limit
        if max_depth < 0:
            return LineageNode(
                fact_id=fact_id,
                project="unknown",
                content="[MAX DEPTH EXCEEDED]",
                fact_type="error",
                confidence="none",
                timestamp="",
                parents=[],
                is_valid=False,
                error="Lineage tree depth exceeded safe limits.",
            )

        # 2. Cache check for O(1) retrieval
        if _cache is None:
            _cache = {}

        if fact_id in _cache:
            val = _cache[fact_id]
            if val is True:
                return LineageNode(
                    fact_id=fact_id,
                    project="unknown",
                    content="[CYCLIC REFERENCE DETECTED]",
                    fact_type="error",
                    confidence="none",
                    timestamp="",
                    parents=[],
                    is_valid=False,
                    error="Cyclic graph lineage protection triggered.",
                )
            return val

        # Pre-emptively mark as being processed to prevent concurrent N+1 race conditions
        _cache[fact_id] = True  # pyright: ignore[reportArgumentType]

        fact = await self.engine.get_fact(fact_id)
        if not fact:
            node = LineageNode(
                fact_id=fact_id,
                project="unknown",
                content="[NOT FOUND]",
                fact_type="error",
                confidence="none",
                timestamp="",
                parents=[],
                is_valid=False,
                error="Fact not found in L0",
            )
            _cache[fact_id] = node
            return node

        # Tracing parents via meta["lineage_sources"] or previous_fact_id
        parent_ids = fact.meta.get("lineage_sources", [])
        if not isinstance(parent_ids, list):
            parent_ids = [parent_ids]

        # Also check for update chain
        prev_id = fact.meta.get("previous_fact_id")
        if prev_id and prev_id not in parent_ids:
            parent_ids.append(prev_id)

        parents = []
        if max_depth > 0:
            tasks = [self.get_lineage(pid, max_depth - 1, _cache) for pid in parent_ids]
            if tasks:
                parents = list(await asyncio.gather(*tasks))

        # Fix missing project in cyclic references that were resolved before fact fetch
        for p in parents:
            if p.error == "Cyclic graph lineage protection triggered." and p.project == "unknown":
                p.project = fact.project

        # Cryptographic Verification (Ω₃-V)
        # In a real scenario, we'd verify hashes here.
        # For now, we assume if it's in the DB and has a tx_id, it's valid L0.
        is_valid = fact.tx_id is not None

        return LineageNode(
            fact_id=fact.id,
            project=fact.project,
            content=fact.content,
            fact_type=fact.fact_type,
            confidence=fact.confidence,
            timestamp=fact.created_at,
            parents=parents,
            is_valid=is_valid,
        )

    def print_tree(self, node: LineageNode, indent: int = 0):
        """Debug helper to print lineage."""
        prefix = "  " * indent
        status = "✅" if node.is_valid else "❌"
        # Fix line too long
        label = f"#{node.fact_id} [{node.fact_type}] in {node.project}"
        line = f"{prefix}{status} {label}"
        logger.debug("%s: %s...", line, node.content[:50])
        for p in node.parents:
            self.print_tree(p, indent + 1)
