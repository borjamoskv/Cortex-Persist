"""Backward-compatible engine delegation helpers."""

# pyright: reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

import logging
from typing import Any

from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN
from cortex.engine.models import row_to_fact

logger = logging.getLogger("cortex.engine.guards")


class CompatibilityMixin:
    """Keeps legacy engine entry points thin and focused."""

    @staticmethod
    def _audit_log(
        action: str,
        fact_type: str = "",
        project: str = "",
        tenant_id: str = "default",
    ) -> None:
        """Append-only audit log for CLI/SDK access to CORTEX memory."""
        audit_logger = logging.getLogger("cortex.audit")
        audit_logger.info(
            "AUDIT: action=%s fact_type=%s project=%s tenant=%s",
            action,
            fact_type,
            project,
            tenant_id,
        )

    async def store(self, *args: Any, **kwargs: Any) -> Any:
        self._synthesize_skill("store")
        self._audit_log(
            "store",
            fact_type=kwargs.get("fact_type", ""),
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await self.facts.store(*args, **kwargs)

    async def store_many(self, *args: Any, **kwargs: Any) -> Any:
        self._synthesize_skill("store")
        return await super().store_many(*args, **kwargs)

    async def recall(self, *args: Any, **kwargs: Any) -> Any:
        self._synthesize_skill("search")
        self._audit_log(
            "recall",
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await super().recall(*args, **kwargs)

    async def search(self, *args: Any, **kwargs: Any) -> Any:
        self._synthesize_skill("search")
        return await super().search(*args, **kwargs)

    async def query(self, *args: Any, **kwargs: Any) -> Any:
        self._synthesize_skill("query")
        return await super().query(*args, **kwargs)

    async def write_optimized(self, *args: Any, **kwargs: Any) -> Any:
        self._synthesize_skill("optimization")
        return await super().write_optimized(*args, **kwargs)

    async def get_fact(self, fact_id: int, tenant_id: str = "default") -> Any:
        self._synthesize_skill("query")
        res = await super().get_fact(fact_id, tenant_id=tenant_id)
        if not res:
            return None
        from cortex.engine.models import Fact

        return Fact(**{k: v for k, v in res.items() if k in Fact.__dataclass_fields__})

    async def retrieve(self, fact_id: int) -> Any:
        """Retrieve an active fact. Raises FactNotFound if missing or deprecated."""
        from cortex.utils.errors import FactNotFound

        async with self.session() as conn:
            async with conn.execute(
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.id = ?",
                (fact_id,),
            ) as cursor:
                row = await cursor.fetchone()
        fact = row_to_fact(tuple(row)) if row else None
        if not fact or fact.valid_until:
            raise FactNotFound(f"Fact {fact_id} not found or deprecated")
        return fact

    async def vote_v2(self, *args: Any, **kwargs: Any) -> Any:
        return await self.consensus.vote_v2(*args, **kwargs)

    async def get_votes(self, fact_id: int, tenant_id: str = "default") -> list[dict[str, Any]]:
        return await self.consensus.get_votes(fact_id, tenant_id=tenant_id)

    async def verify_ledger(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._synthesize_skill("tx")
        return await super().verify_ledger(*args, **kwargs)

    async def propagate_taint(
        self,
        fact_id: int,
        tenant_id: str = "default",
        floor_to_c1: bool = True,
    ) -> Any:
        from cortex.engine.causality import AsyncCausalGraph

        async with self.session() as conn:
            graph = AsyncCausalGraph(conn)
            await graph.ensure_table()
            return await graph.propagate_taint(
                fact_id=fact_id,
                tenant_id=tenant_id,
                floor_to_c1=floor_to_c1,
            )

    async def get_all_active_facts(self, *args: Any, **kwargs: Any) -> list[Any]:
        """Retrieve all active facts across all projects, wrapped in models."""
        results = await super().get_all_active_facts(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def history(self, *args: Any, **kwargs: Any) -> list[Any]:
        """Retrieve historical facts wrapped in models."""
        results = await super().history(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def get_causal_chain(self, *args: Any, **kwargs: Any) -> list[Any]:
        """Retrieve causal chain facts wrapped in models."""
        results = await super().get_causal_chain(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def shannon_report(self, project: str | None = None) -> dict[str, Any]:
        """Shannon entropy analysis of stored memory."""
        from cortex.extensions.shannon.report import EntropyReport

        return await EntropyReport.analyze(self, project)

    async def fingerprint(
        self,
        project: str | None = None,
        top_domains: int = 15,
    ) -> Any:
        """Extract behavioral patterns from the ledger."""
        from cortex.extensions.fingerprint.extractor import FingerprintExtractor

        return await FingerprintExtractor.extract(self, project, top_domains)

    async def immortality_index(self, project: str | None = None) -> dict[str, Any]:
        """Immortality Index (ι) — cognitive crystallization metric."""
        from cortex.extensions.shannon.immortality import ImmortalityIndex

        return await ImmortalityIndex.compute(self, project)

    async def prioritize(
        self,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list[Any]:
        """Bellman Policy Engine — prioritized action queue."""
        from cortex.extensions.policy import PolicyEngine

        policy = PolicyEngine(self)
        return await policy.evaluate(project=project, tenant_id=tenant_id)
