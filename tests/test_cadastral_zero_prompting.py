# SPDX-License-Identifier: Apache-2.0
"""Tests for Cadastral Perimeter Check and Axioma Ω₇ Zero-Prompting Evolution."""

from __future__ import annotations

import pytest

from cortex.engine.evolution_metrics import CortexMetrics
from cortex.engine.evolution_types import (
    DomainMetrics,
    Mutation,
    SovereignAgent,
    SubAgent,
)
from cortex.engine.zero_prompting import (
    ResolutionReport,
    ZeroPromptingEvolutionStrategy,
)
from cortex.skills.cadastral.engine import CadastralEngine
from cortex.skills.cadastral.models import (
    CadastralReport,
    Coordinate,
    ExpropiationStatus,
    OwnershipType,
    Parcel,
    RiskLevel,
    ZoneClassification,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIXTURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def bilbao() -> Coordinate:
    """Bilbao city center."""
    return Coordinate(latitude=43.2630, longitude=-2.9350)


@pytest.fixture
def sovereign_parcel(bilbao: Coordinate) -> Parcel:
    """A sovereign-grade abandoned public parcel."""
    return Parcel(
        parcel_id="P-001",
        coordinates=[bilbao],
        zone=ZoneClassification.ABANDONED_PUBLIC,
        ownership=OwnershipType.PUBLIC_STATE,
        expropriation=ExpropiationStatus.NONE,
        area_m2=5000.0,
        municipality="Bilbao",
        region="Bizkaia",
        country_code="ES",
    )


@pytest.fixture
def forbidden_parcel() -> Parcel:
    """A military-restricted private parcel."""
    return Parcel(
        parcel_id="P-002",
        coordinates=[Coordinate(43.27, -2.94)],
        zone=ZoneClassification.MILITARY_RESTRICTED,
        ownership=OwnershipType.PRIVATE_CORPORATE,
        expropriation=ExpropiationStatus.NONE,
        area_m2=100000.0,
        municipality="Getxo",
    )


@pytest.fixture
def blind_spot_parcel() -> Parcel:
    """A parcel in legal limbo — contested ownership, active expropriation."""
    return Parcel(
        parcel_id="P-003",
        coordinates=[Coordinate(43.25, -2.92)],
        zone=ZoneClassification.RURAL_UNCLAIMED,
        ownership=OwnershipType.CONTESTED,
        expropriation=ExpropiationStatus.ACTIVE,
        area_m2=12000.0,
        municipality="Durango",
    )


@pytest.fixture
def engine() -> CadastralEngine:
    return CadastralEngine()


@pytest.fixture
def subagent_high_fitness() -> SubAgent:
    """SubAgent with fitness > 60 to pass the ZP gate."""
    m = Mutation(mutation_id="agent-zp-01", parameters={"base": 1.0})
    m.history_log = [f"entry-{i}" for i in range(10)]
    return SubAgent(
        agent_id="agent-zp-01",
        mutation=m,
        domain_id="EVOLUTION_CORE",
        fitness=80.0,
        generation=10,
    )


@pytest.fixture
def sovereign_agent(subagent_high_fitness: SubAgent) -> SovereignAgent:
    return SovereignAgent(
        sovereign_id="sov-zp-01",
        domain_id="EVOLUTION_CORE",
        subagents=[subagent_high_fitness],
    )


@pytest.fixture
def high_entropy_metrics() -> DomainMetrics:
    """Metrics with ghost_density and error_rate above thresholds."""
    return DomainMetrics(
        domain_id="EVOLUTION_CORE",
        health_score=0.4,
        error_rate=0.7,
        ghost_density=0.5,
        fact_density=50.0,
        bridge_score=0.3,
        fitness_delta=0.0,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS — CADASTRAL MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCoordinate:
    def test_valid_coordinate(self) -> None:
        c = Coordinate(43.26, -2.93)
        assert c.latitude == 43.26
        assert c.longitude == -2.93
        assert c.as_tuple == (43.26, -2.93)

    def test_invalid_latitude(self) -> None:
        with pytest.raises(ValueError, match="Latitude"):
            Coordinate(91.0, 0.0)

    def test_invalid_longitude(self) -> None:
        with pytest.raises(ValueError, match="Longitude"):
            Coordinate(0.0, 181.0)

    def test_frozen(self) -> None:
        c = Coordinate(43.26, -2.93)
        with pytest.raises(AttributeError):
            c.latitude = 0.0  # type: ignore[misc]


class TestCadastralReport:
    def test_compute_hash_deterministic(self) -> None:
        r = CadastralReport(report_id="test-001", timestamp=1000.0)
        h1 = r.compute_hash()
        h2 = r.compute_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_summary(self) -> None:
        r = CadastralReport(
            report_id="test-sum-001",
            total_parcels_scanned=10,
            sovereign_zones_found=3,
            forbidden_zones_found=2,
        )
        assert "10 parcels" in r.summary
        assert "3 sovereign" in r.summary


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS — CADASTRAL ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCadastralEngine:
    def test_register_and_status(self, engine: CadastralEngine, sovereign_parcel: Parcel) -> None:
        engine.register_parcel(sovereign_parcel)
        status = engine.get_status()
        assert status["registered_parcels"] == 1

    def test_assess_risk_sovereign(self, engine: CadastralEngine, sovereign_parcel: Parcel) -> None:
        assessment = engine.assess_risk(sovereign_parcel)
        assert assessment.risk == RiskLevel.SOVEREIGN
        assert assessment.risk_score < 0.15
        assert "DEPLOY" in assessment.recommendation

    def test_assess_risk_forbidden(self, engine: CadastralEngine, forbidden_parcel: Parcel) -> None:
        assessment = engine.assess_risk(forbidden_parcel)
        assert assessment.risk == RiskLevel.FORBIDDEN
        assert assessment.risk_score >= 0.85
        assert "ABSOLUTE_BLOCK" in assessment.recommendation

    def test_scan_perimeter_finds_blind_spots(
        self,
        engine: CadastralEngine,
        bilbao: Coordinate,
        sovereign_parcel: Parcel,
        forbidden_parcel: Parcel,
        blind_spot_parcel: Parcel,
    ) -> None:
        engine.register_parcels([sovereign_parcel, forbidden_parcel, blind_spot_parcel])
        report = engine.scan_perimeter(bilbao, radius_km=100)

        assert report.total_parcels_scanned == 3
        assert report.sovereign_zones_found >= 1
        assert report.forbidden_zones_found >= 1
        assert len(report.blind_spots) >= 1
        assert report.hash  # SHA-256 computed
        assert len(report.hash) == 64

    def test_scan_perimeter_radius_filter(
        self,
        engine: CadastralEngine,
        sovereign_parcel: Parcel,
    ) -> None:
        engine.register_parcel(sovereign_parcel)
        # Very small radius from a distant point
        far = Coordinate(0.0, 0.0)
        report = engine.scan_perimeter(far, radius_km=1)
        assert report.total_parcels_scanned == 0

    def test_blind_spot_has_legal_gaps(
        self,
        engine: CadastralEngine,
        bilbao: Coordinate,
        blind_spot_parcel: Parcel,
    ) -> None:
        engine.register_parcel(blind_spot_parcel)
        report = engine.scan_perimeter(bilbao, radius_km=100)
        if report.blind_spots:
            bs = report.blind_spots[0]
            assert len(bs.legal_gaps) >= 2  # contested + active expropriation
            assert bs.confidence >= 0.4


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS — ZERO-PROMPTING EVOLUTION (Axioma Ω₇)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestZeroPromptingEvolution:
    def test_fires_on_high_entropy(
        self,
        sovereign_agent: SovereignAgent,
        subagent_high_fitness: SubAgent,
        high_entropy_metrics: DomainMetrics,
    ) -> None:
        strategy = ZeroPromptingEvolutionStrategy()
        cortex_metrics = CortexMetrics(":memory:")
        result = strategy.evaluate(
            sovereign_agent, subagent_high_fitness, high_entropy_metrics, cortex_metrics
        )
        assert result is not None
        assert result["strategy"] == "ZeroPromptingEvolution"
        assert result["axiom"] == "Ω₇"
        assert result["report_hash"]
        assert len(result["report_hash"]) == 64

    def test_does_not_fire_on_low_fitness(
        self,
        high_entropy_metrics: DomainMetrics,
    ) -> None:
        m = Mutation(mutation_id="low-fit", parameters={})
        sub = SubAgent(agent_id="low-fit", mutation=m, domain_id="TEST", fitness=30.0)
        sov = SovereignAgent(sovereign_id="sov", domain_id="TEST", subagents=[sub])
        strategy = ZeroPromptingEvolutionStrategy()
        cortex_metrics = CortexMetrics(":memory:")
        result = strategy.evaluate(sov, sub, high_entropy_metrics, cortex_metrics)
        assert result is None

    def test_does_not_fire_on_low_entropy(
        self,
        sovereign_agent: SovereignAgent,
        subagent_high_fitness: SubAgent,
    ) -> None:
        low_metrics = DomainMetrics(
            domain_id="EVOLUTION_CORE",
            ghost_density=0.05,
            error_rate=0.02,
        )
        strategy = ZeroPromptingEvolutionStrategy()
        cortex_metrics = CortexMetrics(":memory:")
        result = strategy.evaluate(
            sovereign_agent, subagent_high_fitness, low_metrics, cortex_metrics
        )
        assert result is None

    def test_ghost_purge_reduces_history(
        self,
        sovereign_agent: SovereignAgent,
        subagent_high_fitness: SubAgent,
        high_entropy_metrics: DomainMetrics,
    ) -> None:
        initial_log_len = len(subagent_high_fitness.mutation.history_log)
        strategy = ZeroPromptingEvolutionStrategy()
        cortex_metrics = CortexMetrics(":memory:")
        result = strategy.evaluate(
            sovereign_agent, subagent_high_fitness, high_entropy_metrics, cortex_metrics
        )
        assert result is not None
        assert result["resolution"]["ghosts_purged"] > 0
        assert len(subagent_high_fitness.mutation.history_log) < initial_log_len

    def test_resolution_report_hash_chain(
        self,
        sovereign_agent: SovereignAgent,
        subagent_high_fitness: SubAgent,
        high_entropy_metrics: DomainMetrics,
    ) -> None:
        strategy = ZeroPromptingEvolutionStrategy()
        cortex_metrics = CortexMetrics(":memory:")
        strategy.evaluate(
            sovereign_agent, subagent_high_fitness, high_entropy_metrics, cortex_metrics
        )
        hashes = strategy.get_resolution_hashes()
        assert len(hashes) == 1
        assert len(hashes[0]) == 64

    def test_fitness_increases_after_mutation(
        self,
        sovereign_agent: SovereignAgent,
        subagent_high_fitness: SubAgent,
        high_entropy_metrics: DomainMetrics,
    ) -> None:
        initial_fitness = subagent_high_fitness.fitness
        strategy = ZeroPromptingEvolutionStrategy()
        cortex_metrics = CortexMetrics(":memory:")
        result = strategy.evaluate(
            sovereign_agent, subagent_high_fitness, high_entropy_metrics, cortex_metrics
        )
        assert result is not None
        assert subagent_high_fitness.fitness > initial_fitness


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS — AXIOM REGISTRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAxiomRegistry:
    def test_ax029_registered(self) -> None:
        from cortex.axioms.registry import AXIOM_REGISTRY

        ax = AXIOM_REGISTRY.get("AX-029")
        assert ax is not None
        assert "Zero-Prompting" in ax.name
        assert "Ω₇" in ax.name

    def test_total_axiom_count(self) -> None:
        from cortex.axioms.registry import AXIOM_REGISTRY

        assert len(AXIOM_REGISTRY) == 23  # 3 + 10 + 10 (was 22, now 23)


class TestResolutionReport:
    def test_hash_deterministic(self) -> None:
        r = ResolutionReport(
            report_id="test",
            domain_id="TEST",
            agent_id="a1",
            timestamp=1000.0,
            entropy_before=0.5,
            entropy_after=0.3,
            ghosts_purged=2,
            mutations_applied=["m1"],
            fitness_delta=5.0,
        )
        h1 = r.compute_hash()
        h2 = r.compute_hash()
        assert h1 == h2
        assert len(h1) == 64
