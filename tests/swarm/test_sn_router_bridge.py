import pytest
from babylon60.swarm.graph_source import MockSNGraphSource, SalienceCandidate
from babylon60.swarm.router import SwarmRouter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _FakeRegistry:
    _frozen = True
    def snapshot(self): return {"agents": []}
    def get_candidates(self, task): return []


@pytest.fixture
def sn_candidates():
    return [
        SalienceCandidate(agent_id="insula",    region="Insula",     network="SN", salience=0.91, latency_ms=12.0),
        SalienceCandidate(agent_id="acc",       region="ACC",        network="SN", salience=0.85, latency_ms=18.0),
        SalienceCandidate(agent_id="thalamus",  region="Thalamus",   network="SN", salience=0.72, latency_ms=8.0),
    ]


@pytest.fixture
def router(sn_candidates, tmp_path):
    mock_source = MockSNGraphSource(sn_candidates)
    reg = _FakeRegistry()
    r = SwarmRouter(registry=reg, graph_source=mock_source)
    # Redirect ledger DB to temp dir for test isolation
    import babylon60.swarm.ledger.engine as eng
    r.ledger = eng.SwarmLedger(path=str(tmp_path / "test_swarm.db"))
    return r


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sn_router_selects_highest_salience(router):
    result = router.route({"task": "detect anomaly", "context": {}})
    assert result["agent_id"] == "insula"  # salience 0.91 → highest


def test_sn_router_is_deterministic(router):
    req = {"task": "detect anomaly", "context": {"tenant": "x"}}
    a = router.route(req)
    b = router.route(req)
    assert a == b


def test_sn_router_ledger_records_deterministic_signature(router):
    req = {"task": "detect anomaly", "context": {"tenant": "x"}}
    router.route(req)
    router.route(req)

    events = router.ledger.replay("detect anomaly")
    assert len(events) >= 2

    sigs = [e["deterministic_signature"] for e in events]
    assert len(set(sigs)) == 1, "Identical inputs must produce identical signatures"


def test_sn_router_logs_route_decision_event(router):
    router.route({"task": "salience check", "context": {}})
    events = router.ledger.replay("salience check")
    assert len(events) == 1
    assert events[0]["selected_agent"] == "insula"
    assert events[0]["version"] == "v2"
