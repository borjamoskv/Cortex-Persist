import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest

# Asumiendo que el motor MEVTelemetryEngine será implementado en cortex.engine.mev_telemetry
# para monitorizar los eventos del contrato inteligente K2.
from cortex.engine.mev_telemetry import MEVTelemetryEngine, TelemetryAnomaly
from cortex.engine.models import Fact


@pytest.fixture
def mock_cortex_engine():
    class MockEngine:
        def __init__(self):
            self.stored_tasks = []

        async def history(self, project):
            now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()

            return [
                # Caso 1: Violación del invariante de liquidación (HF < 1.0 y Bad Debt no socializado)
                Fact(
                    id=1,
                    tenant_id="default",
                    project="k2-telemetry",
                    content="Liquidation Executed",
                    fact_type="event",
                    tags=["k2", "liquidation", "insolvent"],
                    meta={
                        "confidence": "C5",
                        "health_factor_after": 0.95,
                        "bad_debt_socialized": False,
                        "collateral_amount_base": 1000,
                        "actual_debt_to_cover": 900,
                        "event_type": "liquidation",
                    },
                    created_at=now,
                    updated_at=now,
                    is_tombstoned=False,
                ),
                # Caso 2: Extracción por truncamiento detectada (Ceil-Division Bypass K2-0514-01)
                Fact(
                    id=2,
                    tenant_id="default",
                    project="k2-telemetry",
                    content="Liquidation Executed",
                    fact_type="event",
                    tags=["k2", "liquidation"],
                    meta={
                        "confidence": "C5",
                        "health_factor_after": 1.05,
                        "bad_debt_socialized": False,
                        "collateral_amount_base": 1000,
                        "actual_debt_to_cover": 949,  # Truncated value instead of ceiled
                        "ceil_division_applied": False,
                        "event_type": "liquidation",
                    },
                    created_at=now,
                    updated_at=now,
                    is_tombstoned=False,
                ),
                # Caso 3: Liquidación saludable (HF > 1.0, Ceil division OK)
                Fact(
                    id=3,
                    tenant_id="default",
                    project="k2-telemetry",
                    content="Liquidation Executed",
                    fact_type="event",
                    tags=["k2", "liquidation"],
                    meta={
                        "confidence": "C5",
                        "health_factor_after": 1.10,
                        "bad_debt_socialized": False,
                        "collateral_amount_base": 1000,
                        "actual_debt_to_cover": 950,
                        "ceil_division_applied": True,
                        "event_type": "liquidation",
                    },
                    created_at=now,
                    updated_at=now,
                    is_tombstoned=False,
                ),
            ]

        async def store(self, **kwargs):
            self.stored_tasks.append(kwargs)

    return MockEngine()


@pytest.mark.asyncio
async def test_telemetry_detects_invariant_violation(mock_cortex_engine):
    hunter = MEVTelemetryEngine(mock_cortex_engine)
    report = await hunter.run_full_scan()

    assert report["total_anomalies"] == 2
    assert "LIQUIDATION_INVARIANT_VIOLATION" in report["by_type"]
    assert "TRUNCATION_EXTRACTION_ATTEMPT" in report["by_type"]
    assert report["high_severity"] == 2

    # Verifica que se hayan creado tareas de alerta CORTEX
    assert len(mock_cortex_engine.stored_tasks) == 2
    alert_types = [task["meta"]["anomaly_type"] for task in mock_cortex_engine.stored_tasks]
    assert "LIQUIDATION_INVARIANT_VIOLATION" in alert_types
    assert "TRUNCATION_EXTRACTION_ATTEMPT" in alert_types
