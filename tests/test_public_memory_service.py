from __future__ import annotations

from types import SimpleNamespace

from cortex.extensions.continual_learning import MicroUpdatePlan, MixedBatch
from cortex.services.public_memory import PublicMemoryService


class _FakePublicMemoryEngine:
    def __init__(self) -> None:
        self.store_calls: list[dict[str, object]] = []
        self.search_calls: list[dict[str, object]] = []
        self.store_many_calls: list[list[dict[str, object]]] = []
        self.get_fact_calls: list[dict[str, object]] = []
        self.deprecate_calls: list[dict[str, object]] = []
        self.verify_ledger_calls = 0
        self.causal_chain_calls: list[dict[str, object]] = []
        self.memory = _FakeContinualManager()

    async def store(self, **kwargs):
        self.store_calls.append(kwargs)
        return 42

    async def store_many(self, facts: list[dict[str, object]]):
        self.store_many_calls.append(facts)
        return [1, 2]

    async def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return [
            SimpleNamespace(
                fact_id=7,
                project="alpha",
                content="service search result",
                fact_type="decision",
                score=0.9,
                tags=["edge"],
                created_at="2026-04-07T00:00:00Z",
                updated_at="2026-04-07T00:00:01Z",
                meta={"source": "unit"},
                tx_id=5,
                hash="hash-7",
                graph_context={"graph": {"nodes": []}},
            )
        ]

    async def get_fact(self, **kwargs):
        self.get_fact_calls.append(kwargs)
        if kwargs["fact_id"] == 404:
            return None
        return {
            "id": kwargs["fact_id"],
            "project": "alpha",
            "content": "stored fact",
            "fact_type": "knowledge",
            "tags": ["t1"],
            "created_at": "2026-04-07T00:00:00Z",
            "updated_at": "2026-04-07T00:00:01Z",
            "tenant_id": kwargs.get("tenant_id"),
            "hash": "hash-fact",
        }

    async def deprecate(self, fact_id: int, *, reason: str):
        self.deprecate_calls.append({"fact_id": fact_id, "reason": reason})
        return True

    async def verify_ledger(self):
        self.verify_ledger_calls += 1
        return {"valid": True, "tx_count": 11, "roots_checked": 3}

    async def get_causal_chain(self, **kwargs):
        self.causal_chain_calls.append(kwargs)
        return [{"id": kwargs["fact_id"], "project": "alpha"}]

    async def stats(self):
        return {
            "total_facts": 12,
            "active_facts": 9,
            "deprecated_facts": 3,
            "project_count": 4,
            "embeddings": 8,
            "transactions": 21,
            "db_size_mb": 1.5,
        }


class _FakeContinualManager:
    def __init__(self) -> None:
        self.status_calls: list[dict[str, object]] = []
        self.plan_calls: list[dict[str, object]] = []
        self.execute_calls: list[dict[str, object]] = []
        self.forget_calls: list[dict[str, object]] = []

    async def continual_learning_status(self, **kwargs):
        self.status_calls.append(kwargs)
        return {"enabled": True, "tenant_id": kwargs["tenant_id"], "domain": kwargs.get("domain")}

    async def plan_continual_update(self, **kwargs):
        self.plan_calls.append(kwargs)
        return MicroUpdatePlan(
            tenant_id=str(kwargs["tenant_id"]),
            domain=str(kwargs["domain"]),
            adapter_id="lora:test",
            learning_rate=5e-5,
            risk_score=0.2,
            batch=MixedBatch(),
        )

    async def execute_continual_update(self, **kwargs):
        self.execute_calls.append(kwargs)
        return {
            "committed": True,
            "plan": {
                "tenant_id": kwargs["tenant_id"],
                "domain": kwargs["domain"],
            },
        }

    async def forget_continual_memory(self, **kwargs):
        self.forget_calls.append(kwargs)
        return {"deleted_exp_ids": ["exp-1"], "query": kwargs["query"]}


async def test_public_memory_service_store_omits_unset_tenant() -> None:
    engine = _FakePublicMemoryEngine()
    service = PublicMemoryService(engine)

    result = await service.store(
        project="alpha",
        content="stored via service",
        fact_type="decision",
        tags=["tag-a"],
        source="mcp-test",
        confidence="stated",
    )

    assert result.fact_id == 42
    assert engine.store_calls == [
        {
            "project": "alpha",
            "content": "stored via service",
            "fact_type": "decision",
            "tags": ["tag-a"],
            "source": "mcp-test",
            "confidence": "stated",
        }
    ]


async def test_public_memory_service_search_preserves_null_filters_when_requested() -> None:
    engine = _FakePublicMemoryEngine()
    service = PublicMemoryService(engine)

    results = await service.search(
        query="where is alpha",
        top_k=7,
        project="alpha",
        tenant_id="tenant-search",
        as_of="2026-04-07T00:00:00Z",
        fact_type=None,
        tags=["edge"],
        graph_depth=0,
        include_graph=False,
        preserve_null_filters=True,
    )

    assert engine.search_calls == [
        {
            "query": "where is alpha",
            "top_k": 7,
            "project": "alpha",
            "tenant_id": "tenant-search",
            "as_of": "2026-04-07T00:00:00Z",
            "fact_type": None,
            "tags": ["edge"],
            "graph_depth": 0,
            "include_graph": False,
        }
    ]
    assert results[0].fact_id == 7
    assert results[0].context == {"graph": {"nodes": []}}


async def test_public_memory_service_batch_verify_and_chain_are_canonical() -> None:
    engine = _FakePublicMemoryEngine()
    service = PublicMemoryService(engine)

    stored_ids = await service.batch_store(
        [
            {"project": "alpha", "content": "a", "tenant_id": "tenant-a"},
            {"project": "beta", "content": "b", "tenant_id": "tenant-a"},
        ]
    )
    report = await service.verify_ledger()
    chain = await service.causal_chain(fact_id=7, direction="up", max_depth=3, tenant_id="tenant-a")

    assert stored_ids == [1, 2]
    assert engine.store_many_calls == [
        [
            {"project": "alpha", "content": "a", "tenant_id": "tenant-a"},
            {"project": "beta", "content": "b", "tenant_id": "tenant-a"},
        ]
    ]
    assert report == {
        "valid": True,
        "violations": 0,
        "transactions_checked": 11,
        "roots_checked": 3,
    }
    assert chain == [{"id": 7, "project": "alpha"}]
    assert engine.causal_chain_calls == [
        {"fact_id": 7, "direction": "up", "max_depth": 3, "tenant_id": "tenant-a"}
    ]


async def test_public_memory_service_get_fact_and_deprecate() -> None:
    engine = _FakePublicMemoryEngine()
    service = PublicMemoryService(engine)

    fact = await service.get_fact(7, tenant_id="tenant-a")
    fact_record = await service.get_fact_record(7, tenant_id="tenant-a")
    missing = await service.get_fact(404, tenant_id="tenant-a")
    success = await service.deprecate(7, reason="api_deleted")

    assert fact is not None
    assert fact.id == 7
    assert fact_record is not None
    assert fact_record["tenant_id"] == "tenant-a"
    assert missing is None
    assert success is True
    assert engine.deprecate_calls == [{"fact_id": 7, "reason": "api_deleted"}]


async def test_public_memory_service_status_maps_engine_stats() -> None:
    engine = _FakePublicMemoryEngine()
    service = PublicMemoryService(engine)

    status = await service.status()

    assert status.total_facts == 12
    assert status.active_facts == 9
    assert status.projects == 4
    assert status.transactions == 21


async def test_public_memory_service_exposes_continual_learning_manager() -> None:
    engine = _FakePublicMemoryEngine()
    service = PublicMemoryService(engine)

    status = await service.continual_learning_status(tenant_id="tenant-a", domain="support")
    plan = await service.plan_continual_update(
        tenant_id="tenant-a",
        domain="support",
        policy_violation=True,
    )
    execution = await service.execute_continual_update(
        tenant_id="tenant-a",
        domain="support",
        policy_violation=True,
        critical_domains=["support"],
    )
    forget = await service.forget_continual_memory(
        tenant_id="tenant-a",
        user_id="user-1",
        query="secret",
    )

    assert status == {"enabled": True, "tenant_id": "tenant-a", "domain": "support"}
    assert plan is not None
    assert plan["adapter_id"] == "lora:test"
    assert execution == {
        "committed": True,
        "plan": {"tenant_id": "tenant-a", "domain": "support"},
    }
    assert forget == {"deleted_exp_ids": ["exp-1"], "query": "secret"}
    assert engine.memory.status_calls == [
        {"tenant_id": "tenant-a", "domain": "support"}
    ]
    assert engine.memory.plan_calls == [
        {"tenant_id": "tenant-a", "domain": "support", "policy_violation": True}
    ]
    assert engine.memory.execute_calls == [
        {
            "tenant_id": "tenant-a",
            "domain": "support",
            "policy_violation": True,
            "critical_domains": ["support"],
        }
    ]
    assert engine.memory.forget_calls == [
        {"tenant_id": "tenant-a", "user_id": "user-1", "query": "secret"}
    ]


async def test_public_memory_service_continual_learning_disabled_without_manager() -> None:
    engine = _FakePublicMemoryEngine()
    engine.memory = None
    service = PublicMemoryService(engine)

    status = await service.continual_learning_status(tenant_id="tenant-a", domain="support")
    plan = await service.plan_continual_update(tenant_id="tenant-a", domain="support")
    execution = await service.execute_continual_update(tenant_id="tenant-a", domain="support")
    forget = await service.forget_continual_memory(
        tenant_id="tenant-a",
        user_id="user-1",
        query="secret",
    )

    assert status == {"enabled": False, "tenant_id": "tenant-a", "domain": "support"}
    assert plan is None
    assert execution is None
    assert forget is None
