from datetime import datetime, timedelta, timezone

import pytest

from cortex.engine.anomaly_hunter import AnomalyHunterEngine


@pytest.fixture
def mock_cortex_engine():
    class MockEngine:
        async def history(self, project):
            fact_1_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            fact_2_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            
            return [
                {
                    "id": 1,
                    "tenant_id": "default",
                    "project": "anomaly-hunter",
                    "content": "Ruta X bloqueada",
                    "fact_type": "event",
                    "tags": ["route_x"],
                    "meta": {
                        "confidence": "C5",
                        "valid_from": fact_1_time,
                        "valid_until": None,
                        "source": "sensor",
                        "consensus_score": 1.0,
                    },
                    "created_at": fact_1_time,
                    "updated_at": fact_1_time,
                    "is_tombstoned": False,
                },
                {
                    "id": 2,
                    "tenant_id": "default",
                    "project": "anomaly-hunter",
                    "content": "Pasé por Ruta X",
                    "fact_type": "event",
                    "tags": ["route_x"],
                    "meta": {
                        "confidence": "C5",
                        "valid_from": fact_2_time,
                        "valid_until": None,
                        "source": "sensor",
                        "consensus_score": 1.0,
                    },
                    "created_at": fact_2_time,
                    "updated_at": fact_2_time,
                    "is_tombstoned": False,
                }
            ]
            
        async def get_fact(self, fact_id):
            return None
            
        async def get_causal_chain(self, fact_id):
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
