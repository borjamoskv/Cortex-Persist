import time
from datetime import datetime, timedelta, timezone

import pytest

from cortex.engine.anomaly_hunter import AnomalyHunterEngine
from cortex.engine.models import Fact


@pytest.fixture
def mock_cortex_engine():
    class MockEngine:
        async def history(self, project):
            fact_1_time = (
                datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=2)
            ).isoformat()
            fact_2_time = (
                datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=1)
            ).isoformat()

            return [
                Fact(
                    id=1,
                    tenant_id="default",
                    project="anomaly-hunter",
                    content="Ruta X bloqueada",
                    fact_type="event",
                    tags=["route_x"],
                    meta={
                        "confidence": "C5",
                        "valid_from": fact_1_time,
                        "valid_until": None,
                        "source": "sensor",
                    },
                    created_at=fact_1_time,
                    updated_at=fact_1_time,
                    is_tombstoned=False,
                ),
                Fact(
                    id=2,
                    tenant_id="default",
                    project="anomaly-hunter",
                    content="Pasé por Ruta X",
                    fact_type="event",
                    tags=["route_x"],
                    meta={
                        "confidence": "C5",
                        "valid_from": fact_2_time,
                        "valid_until": None,
                        "source": "sensor",
                    },
                    created_at=fact_2_time,
                    updated_at=fact_2_time,
                    is_tombstoned=False,
                ),
            ]

        async def get_fact(self, fact_id):
            # For temporal inversion test
            if fact_id == 1:
                return {
                    "created_at": (
                        datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=1)
                    ).isoformat()
                }
            elif fact_id == 2:
                return {
                    "created_at": (
                        datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=2)
                    ).isoformat()
                }
            return None

        async def get_causal_chain(self, fact_id):
            # For confidence collapse test
            if fact_id == 3:
                return [
                    Fact(
                        id=10,
                        tenant_id="default",
                        project="test",
                        content="",
                        fact_type="event",
                        confidence="C1",
                        created_at="",
                    ),
                    Fact(
                        id=11,
                        tenant_id="default",
                        project="test",
                        content="",
                        fact_type="event",
                        confidence="C2",
                        created_at="",
                    ),
                    Fact(
                        id=12,
                        tenant_id="default",
                        project="test",
                        content="",
                        fact_type="event",
                        confidence="C3",
                        created_at="",
                    ),
                ]
            return []

        async def store(self, **kwargs):
            pass

    return MockEngine()


@pytest.mark.asyncio
async def test_anomaly_hunter_spatial_contradiction(mock_cortex_engine):
    hunter = AnomalyHunterEngine(mock_cortex_engine)
    report = await hunter.run_full_scan()

    assert report["total_anomalies"] == 1
    assert "SPATIAL_CONTRADICTION" in report["by_type"]
    assert report["high_severity"] == 1


@pytest.mark.asyncio
async def test_anomaly_hunter_temporal_inversion(mock_cortex_engine):
    # Setup facts where effect (fact 2) has an older timestamp than cause (fact 1)
    fact_1_time = (
        datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=1)
    ).isoformat()
    fact_2_time = (
        datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=2)
    ).isoformat()

    facts = [
        Fact(
            id=2,
            tenant_id="default",
            project="test",
            content="Effect",
            fact_type="event",
            created_at=fact_2_time,
            meta={"caused_by": 1},
        )
    ]

    hunter = AnomalyHunterEngine(mock_cortex_engine)
    inversions = await hunter.detect_temporal_inversions(facts)

    assert len(inversions) == 1
    assert inversions[0].type == "TEMPORAL_INVERSION"
    assert inversions[0].severity == "HIGH"
    assert inversions[0].facts_involved == [2, 1]


@pytest.mark.asyncio
async def test_anomaly_hunter_value_drift():
    # Setup facts with divergent values for the same entity
    fact_1_time = (
        datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=2)
    ).isoformat()
    fact_2_time = (
        datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(hours=1)
    ).isoformat()

    facts = [
        Fact(
            id=1,
            tenant_id="default",
            project="test",
            content="Value 1",
            fact_type="event",
            tags=["entity_x"],
            created_at=fact_1_time,
            meta={"value": 100},
        ),
        Fact(
            id=2,
            tenant_id="default",
            project="test",
            content="Value 2",
            fact_type="event",
            tags=["entity_x"],
            created_at=fact_2_time,
            meta={"value": 200},
        ),
    ]

    # Mock engine is not needed for value drift
    hunter = AnomalyHunterEngine(None)
    drifts = await hunter.detect_value_drift(facts)

    assert len(drifts) == 1
    assert drifts[0].type == "VALUE_DRIFT"
    assert drifts[0].severity == "MEDIUM"
    assert drifts[0].facts_involved == [1, 2]


@pytest.mark.asyncio
async def test_anomaly_hunter_ghost_resurrection():
    facts = [
        Fact(
            id=1,
            tenant_id="default",
            project="test",
            content="Entity resurrected",
            fact_type="event",
            meta={},
        ),
        Fact(
            id=2,
            tenant_id="default",
            project="test",
            content="Normal entity",
            fact_type="event",
            meta={"reopened": True},
        ),
    ]

    hunter = AnomalyHunterEngine(None)
    resurrections = await hunter.detect_ghost_resurrections(facts)

    assert len(resurrections) == 2
    assert resurrections[0].type == "GHOST_RESURRECTION"
    assert resurrections[1].type == "GHOST_RESURRECTION"
    assert resurrections[0].severity == "LOW"


@pytest.mark.asyncio
async def test_anomaly_hunter_confidence_collapse(mock_cortex_engine):
    facts = [
        Fact(id=3, tenant_id="default", project="test", content="Conclusion", fact_type="event")
    ]

    hunter = AnomalyHunterEngine(mock_cortex_engine)
    collapses = await hunter.detect_confidence_collapses(facts)

    assert len(collapses) == 1
    assert collapses[0].type == "CONFIDENCE_COLLAPSE"
    assert collapses[0].severity == "MEDIUM"
    assert collapses[0].facts_involved == [10, 11, 12]
