# pyright: reportAttributeAccessIssue=false
class LegacyMixin:
    # Backward Compatibility Aliases & Delegation

    async def store(self, *args, **kwargs):
        self._synthesize_skill("store")
        self._audit_log(
            "store",
            fact_type=kwargs.get("fact_type", ""),
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await self.facts.store(*args, **kwargs)

    async def store_many(self, *args, **kwargs):
        self._synthesize_skill("store")
        return await super().store_many(*args, **kwargs)

    async def recall(self, *args, **kwargs):
        self._synthesize_skill("search")
        self._audit_log(
            "recall",
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await super().recall(*args, **kwargs)

    async def search(self, *args, **kwargs):
        self._synthesize_skill("search")
        return await super().search(*args, **kwargs)

    async def query(self, *args, **kwargs):
        self._synthesize_skill("query")
        return await super().query(*args, **kwargs)

    async def write_optimized(self, *args, **kwargs):
        self._synthesize_skill("optimization")
        return await super().write_optimized(*args, **kwargs)

    async def get_fact(self, fact_id: int, tenant_id: str = "default"):
        self._synthesize_skill("query")
        res = await super().get_fact(fact_id, tenant_id=tenant_id)
        if not res:
            return None
        from cortex.engine.models import Fact

        return Fact(**{k: v for k, v in res.items() if k in Fact.__dataclass_fields__})

    async def retrieve(self, fact_id: int):
        from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN
        from cortex.engine.models import row_to_fact
        from cortex.utils.errors import FactNotFound

        async with self.session() as conn:
            async with conn.execute(
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.id = ?", (fact_id,)
            ) as cursor:
                row = await cursor.fetchone()
        fact = row_to_fact(tuple(row)) if row else None
        if not fact or fact.valid_until:
            raise FactNotFound(f"Fact {fact_id} not found or deprecated")
        return fact

    async def vote_v2(self, *args, **kwargs):
        return await self.consensus.vote_v2(*args, **kwargs)

    async def get_all_active_facts(self, *args, **kwargs):
        results = await super().get_all_active_facts(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def history(self, *args, **kwargs):
        results = await super().history(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def get_causal_chain(self, *args, **kwargs):
        results = await super().get_causal_chain(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]
