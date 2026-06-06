# [C5-REAL] Exergy-Maximized
"""CORTEX Engine - Delegated Methods Mixin.

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN
from cortex.engine.models import row_to_fact

logger = logging.getLogger("cortex.engine.guards")


class DelegatesMixin:
    """Mixin containing compatibility delegates and extension wrappers for CortexEngine."""

    async def recall_episode(
        self,
        query: str,
        project: str = "",
        limit: int = 3,
        tenant_id: str = "default",
    ) -> list:
        """Recall causal episodes matching a query."""
        from cortex.memory.episodic import CausalTracer

        async with self.session() as conn:  # pyright: ignore[reportAttributeAccessIssue]
            tracer = CausalTracer(conn)
            resolved_tenant_id = self._resolve_tenant(tenant_id)  # pyright: ignore[reportAttributeAccessIssue]
            return await tracer.recall_episode(query, project, limit, tenant_id=resolved_tenant_id)

    async def trace_episode(
        self,
        fact_id: int,
        max_depth: int | None = None,
        tenant_id: str = "default",
    ):
        """Trace the full causal DAG from a given fact ID."""
        from cortex.memory.episodic import CausalTracer

        async with self.session() as conn:  # pyright: ignore[reportAttributeAccessIssue]
            tracer = CausalTracer(conn)
            resolved_tenant_id = self._resolve_tenant(tenant_id)  # pyright: ignore[reportAttributeAccessIssue]
            return await tracer.trace_episode(fact_id, max_depth, tenant_id=resolved_tenant_id)

    async def store(self, *args, **kwargs):
        self._synthesize_skill("store")  # pyright: ignore[reportAttributeAccessIssue]
        self._audit_log(  # pyright: ignore[reportAttributeAccessIssue]
            "store",
            fact_type=kwargs.get("fact_type", ""),
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await self.facts.store(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def store_many(self, *args, **kwargs):
        self._synthesize_skill("store")  # pyright: ignore[reportAttributeAccessIssue]
        return await super().store_many(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def recall(self, *args, **kwargs):
        self._synthesize_skill("search")  # pyright: ignore[reportAttributeAccessIssue]
        self._audit_log(  # pyright: ignore[reportAttributeAccessIssue]
            "recall",
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await super().recall(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def search(self, *args, **kwargs):
        self._synthesize_skill("search")  # pyright: ignore[reportAttributeAccessIssue]
        return await super().search(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def query(self, *args, **kwargs):
        self._synthesize_skill("query")  # pyright: ignore[reportAttributeAccessIssue]
        return await super().query(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def write_optimized(self, *args, **kwargs):
        self._synthesize_skill("optimization")  # pyright: ignore[reportAttributeAccessIssue]
        return await super().write_optimized(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def get_fact(self, fact_id: int, tenant_id: str = "default"):
        self._synthesize_skill("query")  # pyright: ignore[reportAttributeAccessIssue]
        res = await super().get_fact(fact_id, tenant_id=tenant_id)  # pyright: ignore[reportAttributeAccessIssue]
        if not res:
            return None
        from cortex.engine.models import Fact

        return Fact(**{k: v for k, v in res.items() if k in Fact.__dataclass_fields__})

    async def retrieve(self, fact_id: int):
        """Retrieve an active fact. Raises FactNotFound if missing or deprecated."""
        from cortex.utils.errors import FactNotFound

        async with (
            self.session() as conn,  # pyright: ignore[reportAttributeAccessIssue]
            conn.execute(f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.id = ?", (fact_id,)) as cursor,
        ):
            row = await cursor.fetchone()
        fact = row_to_fact(tuple(row)) if row else None
        if not fact or fact.valid_until:
            raise FactNotFound(f"Fact {fact_id} not found or deprecated")
        return fact

    async def vote_v2(self, *args, **kwargs):
        return await self.consensus.vote_v2(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def get_votes(self, *args, **kwargs):
        return await self.consensus.get_votes(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def verify_vote_ledger(self, *args, **kwargs):
        return await self.consensus.verify_vote_ledger(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]

    async def propagate_taint(self, fact_id: int, tenant_id: str = "default"):
        """Propagate causal taint through the tenant-scoped causality graph."""
        from cortex.engine.causality import AsyncCausalGraph

        tenant_id = self._resolve_tenant(tenant_id)  # pyright: ignore[reportAttributeAccessIssue]
        async with self.session() as conn:  # pyright: ignore[reportAttributeAccessIssue]
            graph = AsyncCausalGraph(conn)
            await graph.ensure_table()
            return await graph.propagate_taint(fact_id, tenant_id=tenant_id)

    def get_trust_registry(self):
        """Return the in-memory trust registry used by trust endpoints."""
        if self._trust_registry is None:
            from cortex.engine.trust_registry import TrustRegistry

            self._trust_registry = TrustRegistry()
        return self._trust_registry

    async def create_checkpoint(self) -> str | None:
        """Create a transaction-ledger Merkle checkpoint."""
        ledger = await self._get_or_create_ledger()  # pyright: ignore[reportAttributeAccessIssue]
        return await ledger.create_checkpoint_async()

    async def get_all_active_facts(self, *args, **kwargs):
        """Retrieve all active facts across all projects, wrapped in models."""
        results = await super().get_all_active_facts(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def history(self, *args, **kwargs):
        """Retrieve historical facts wrapped in models."""
        results = await super().history(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def get_causal_chain(self, *args, **kwargs):
        """Retrieve causal chain facts wrapped in models."""
        results = await super().get_causal_chain(*args, **kwargs)  # pyright: ignore[reportAttributeAccessIssue]
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def shannon_report(self, project: str | None = None) -> dict:
        """Shannon entropy analysis of stored memory."""
        from cortex.extensions.shannon.report import EntropyReport

        return await EntropyReport.analyze(self, project)  # pyright: ignore[reportArgumentType]

    async def fingerprint(
        self,
        project: str | None = None,
        top_domains: int = 15,
    ):
        """Cognitive Fingerprint - extract behavioral patterns from the Ledger."""
        from cortex.extensions.fingerprint.extractor import FingerprintExtractor

        return await FingerprintExtractor.extract(self, project, top_domains)  # pyright: ignore[reportArgumentType]

    async def immortality_index(self, project: str | None = None) -> dict:
        """Immortality Index (ι) - cognitive crystallization metric."""
        from cortex.extensions.shannon.immortality import ImmortalityIndex

        return await ImmortalityIndex.compute(self, project)  # pyright: ignore[reportArgumentType]

    async def prioritize(
        self,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list:
        """Bellman Policy Engine - prioritized action queue."""
        from cortex.extensions.policy import PolicyEngine

        policy = PolicyEngine(self)  # pyright: ignore[reportArgumentType]
        return await policy.evaluate(project=project, tenant_id=tenant_id)

    def export_snapshot(self, out_path: str | Path) -> str:
        from cortex.extensions.sync.snapshot import export_snapshot

        return export_snapshot(self, out_path)  # type: ignore[reportArgumentType,reportReturnType]

    def _row_to_fact(
        self,
        row: aiosqlite.Row | dict,
        tenant_id: str = "default",
    ) -> dict:
        """Delegate to MixinBase (supports tenant-scoped decryption)."""
        return super()._row_to_fact(  # type: ignore[reportAttributeAccessIssue]
            row,
            tenant_id=tenant_id,
        )
