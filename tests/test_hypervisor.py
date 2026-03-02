"""Tests for cortex.hypervisor — The Telescope Inversion Test.

Verifies:
1. Tenant surface is minimal (3 methods, 4 dataclasses)
2. Internal types never leak through the membrane
3. Tenant isolation prevents cross-tenant access
4. Complexity compression strips internal fields
5. Side-effects fire without blocking
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.hypervisor.compressor import ComplexityCompressor
from cortex.hypervisor.isolator import TenantIsolator
from cortex.hypervisor.models import HealthReport, Memory, Receipt

# ── Model Tests ──────────────────────────────────────────────────────


class TestMemory:
    def test_frozen(self):
        m = Memory(
            content="test", relevance=0.8, created=datetime.now(timezone.utc), source="agent"
        )
        with pytest.raises(AttributeError):
            m.content = "modified"  # type: ignore[misc]

    def test_fields_count(self):
        """Memory exposes exactly 4 fields — no more."""
        assert len(fields(Memory)) == 4

    def test_field_names(self):
        names = {f.name for f in fields(Memory)}
        assert names == {"content", "relevance", "created", "source"}


class TestReceipt:
    def test_frozen(self):
        r = Receipt(id="mem_42", project="alpha", stored_at=datetime.now(timezone.utc))
        with pytest.raises(AttributeError):
            r.id = "mem_99"  # type: ignore[misc]

    def test_opaque_id_format(self):
        r = Receipt(id="mem_42", project="alpha", stored_at=datetime.now(timezone.utc))
        assert r.id.startswith("mem_")


class TestHealthReport:
    def test_frozen(self):
        h = HealthReport(
            status="healthy",
            memory_count=10,
            last_activity=datetime.now(timezone.utc),
            integrity="verified",
        )
        with pytest.raises(AttributeError):
            h.status = "critical"  # type: ignore[misc]

    def test_no_internal_fields(self):
        """HealthReport must NOT contain: tx_id, hash, merkle_root, etc."""
        names = {f.name for f in fields(HealthReport)}
        forbidden = {"tx_id", "hash", "merkle_root", "consensus_score", "endocrine_level"}
        assert names & forbidden == set()


# ── Compressor Tests ─────────────────────────────────────────────────


class TestComplexityCompressor:
    def test_fact_to_memory_strips_internals(self):
        """Fact → Memory must strip all CORTEX-internal fields."""
        fact = MagicMock()
        fact.content = "The release is Q2 2026"
        fact.consensus_score = 0.87
        fact.created_at = "2026-03-02T17:00:00+00:00"
        fact.source = "agent:gemini"
        # These exist on Fact but must NOT appear in Memory
        fact.tx_id = 198
        fact.hash = "abc123"
        fact.tenant_id = "secret-tenant"
        fact.id = 42

        memory = ComplexityCompressor.fact_to_memory(fact)

        assert isinstance(memory, Memory)
        assert memory.content == "The release is Q2 2026"
        assert 0.0 <= memory.relevance <= 1.0
        assert isinstance(memory.created, datetime)
        # Verify internals are NOT accessible
        assert not hasattr(memory, "tx_id")
        assert not hasattr(memory, "hash")
        assert not hasattr(memory, "tenant_id")
        assert not hasattr(memory, "id")

    def test_to_receipt_opaque_id(self):
        receipt = ComplexityCompressor.to_receipt(42, "alpha")
        assert receipt.id == "mem_42"
        assert receipt.project == "alpha"

    def test_score_normalization_clamping(self):
        """Scores outside [0, 1] must be clamped."""
        fact_high = MagicMock(content="x", consensus_score=1.5, created_at=None, source="a")
        fact_low = MagicMock(content="x", consensus_score=-0.3, created_at=None, source="a")

        m_high = ComplexityCompressor.fact_to_memory(fact_high)
        m_low = ComplexityCompressor.fact_to_memory(fact_low)

        assert m_high.relevance == 1.0
        assert m_low.relevance == 0.0

    def test_health_report_degraded_on_empty(self):
        report = ComplexityCompressor.to_health_report(
            active_count=0,
            last_activity_iso=None,
            chain_valid=True,
        )
        assert report.status == "degraded"

    def test_health_report_critical_on_chain_break(self):
        report = ComplexityCompressor.to_health_report(
            active_count=100,
            last_activity_iso="2026-03-02T17:00:00",
            chain_valid=False,
        )
        assert report.status == "critical"
        assert report.integrity == "unverified"

    def test_health_report_healthy(self):
        report = ComplexityCompressor.to_health_report(
            active_count=42,
            last_activity_iso="2026-03-02T17:00:00",
            chain_valid=True,
        )
        assert report.status == "healthy"
        assert report.integrity == "verified"
        assert report.memory_count == 42


# ── Isolator Tests ───────────────────────────────────────────────────


class TestTenantIsolator:
    def test_valid_tenant_id(self):
        iso = TenantIsolator("tenant-abc")
        assert iso.tenant_id == "tenant-abc"

    def test_empty_tenant_id_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            TenantIsolator("")

    def test_invalid_chars_raises(self):
        with pytest.raises(ValueError, match="Invalid tenant_id"):
            TenantIsolator("tenant with spaces")

    def test_scope_kwargs_injects_tenant(self):
        iso = TenantIsolator("tenant-xyz")
        result = iso.scope_kwargs(project="alpha", content="test")
        assert result["tenant_id"] == "tenant-xyz"
        assert result["project"] == "alpha"

    def test_scope_kwargs_overrides_manual_tenant(self):
        """Tenant can't override the isolator's tenant_id."""
        iso = TenantIsolator("correct-tenant")
        result = iso.scope_kwargs(tenant_id="hacker-tenant", project="alpha")
        assert result["tenant_id"] == "correct-tenant"


# ── Handle Surface Tests ────────────────────────────────────────────


class TestAgentHandleSurface:
    def test_handle_only_exposes_3_methods(self):
        """The AgentHandle must expose exactly: remember, recall, reflect."""
        from cortex.hypervisor.handle import AgentHandle

        public_methods = [
            m
            for m in dir(AgentHandle)
            if not m.startswith("_") and callable(getattr(AgentHandle, m))
        ]
        assert set(public_methods) == {"remember", "recall", "reflect"}

    def test_handle_has_project_property(self):
        from cortex.hypervisor.handle import AgentHandle

        handle = AgentHandle(tenant="t", project="p", hypervisor=MagicMock())
        assert handle.project == "p"

    def test_handle_repr_no_tenant_leak(self):
        """repr must not leak tenant_id."""
        from cortex.hypervisor.handle import AgentHandle

        handle = AgentHandle(tenant="secret-tenant", project="public-proj", hypervisor=MagicMock())
        r = repr(handle)
        assert "secret-tenant" not in r
        assert "public-proj" in r


# ── Integration Test (AgencyHypervisor) ──────────────────────────────


class TestAgencyHypervisorIntegration:
    @pytest.fixture
    def mock_engine(self):
        engine = AsyncMock()
        engine.store = AsyncMock(return_value=42)
        engine.search = AsyncMock(return_value=[])
        engine.recall = AsyncMock(return_value=[])
        engine.stats = AsyncMock(return_value={"active_facts": 10})
        engine.verify_ledger = AsyncMock(return_value={"valid": True})
        return engine

    @pytest.fixture
    def hypervisor(self, mock_engine):
        from cortex.hypervisor.core import AgencyHypervisor

        return AgencyHypervisor(mock_engine)

    @pytest.mark.asyncio
    async def test_remember_returns_receipt(self, hypervisor):
        handle = hypervisor.create_handle("tenant-a", "project-x")
        receipt = await handle.remember("Important fact for testing")
        assert isinstance(receipt, Receipt)
        assert receipt.id == "mem_42"
        assert receipt.project == "project-x"

    @pytest.mark.asyncio
    async def test_remember_passes_tenant_to_engine(self, hypervisor, mock_engine):
        handle = hypervisor.create_handle("tenant-isolated", "proj")
        await handle.remember("Content here for the test")
        # Verify engine.store was called with the correct tenant_id
        mock_engine.store.assert_called_once()
        call_kwargs = mock_engine.store.call_args[1]
        assert call_kwargs["tenant_id"] == "tenant-isolated"

    @pytest.mark.asyncio
    async def test_recall_returns_memory_list(self, hypervisor):
        handle = hypervisor.create_handle("tenant-b", "proj")
        memories = await handle.recall("what happened?")
        assert isinstance(memories, list)

    @pytest.mark.asyncio
    async def test_reflect_returns_health_report(self, hypervisor):
        handle = hypervisor.create_handle("tenant-c", "proj")
        health = await handle.reflect()
        assert isinstance(health, HealthReport)
        assert health.integrity == "verified"

    @pytest.mark.asyncio
    async def test_tenant_isolation_different_handles(self, hypervisor, mock_engine):
        """Two handles with different tenants must scope independently."""
        h1 = hypervisor.create_handle("tenant-1", "proj")
        h2 = hypervisor.create_handle("tenant-2", "proj")

        await h1.remember("Fact for tenant 1 only")
        call_1 = mock_engine.store.call_args[1]

        mock_engine.store.reset_mock()

        await h2.remember("Fact for tenant 2 only")
        call_2 = mock_engine.store.call_args[1]

        assert call_1["tenant_id"] == "tenant-1"
        assert call_2["tenant_id"] == "tenant-2"


# ── Telescope Inversion Ratio Test ───────────────────────────────────


class TestTelescopeInversion:
    def test_public_api_size(self):
        """The public API must export exactly 5 symbols."""
        import cortex.hypervisor as hv

        assert set(hv.__all__) == {
            "AgencyHypervisor",
            "AgentHandle",
            "HealthReport",
            "Memory",
            "Receipt",
        }

    def test_memory_has_no_internal_fields(self):
        """Memory must contain ZERO CORTEX-internal fields."""
        internal_names = {
            "tx_id",
            "hash",
            "tenant_id",
            "consensus_score",
            "fact_type",
            "valid_from",
            "valid_until",
            "meta",
            "embedding",
            "merkle_root",
            "excitation",
        }
        memory_names = {f.name for f in fields(Memory)}
        leaked = memory_names & internal_names
        assert leaked == set(), f"Internal fields leaked to tenant surface: {leaked}"
