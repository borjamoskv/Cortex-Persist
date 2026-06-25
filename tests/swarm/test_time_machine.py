import pytest
from legacy_research.swarm.graph_source import MockSNGraphSource, SalienceCandidate
from legacy_research.swarm.router import SwarmRouter
from legacy_research.swarm.ledger import SwarmLedger, SwarmTimeMachine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _FakeRegistry:
    _frozen = True
    def snapshot(self): return {"agents": []}
    def get_candidates(self, task): return []


@pytest.fixture
def candidates():
    return [
        SalienceCandidate(agent_id="insula",   region="Insula",  network="SN", salience=0.91, latency_ms=12.0),
        SalienceCandidate(agent_id="acc",      region="ACC",     network="SN", salience=0.85, latency_ms=18.0),
        SalienceCandidate(agent_id="thalamus", region="Thalamus",network="SN", salience=0.72, latency_ms=8.0),
    ]


@pytest.fixture
def router_and_tm(candidates, tmp_path):
    mock_source = MockSNGraphSource(candidates)
    r = SwarmRouter(registry=_FakeRegistry(), graph_source=mock_source)
    import legacy_research.swarm.ledger.engine as eng
    r.ledger = eng.SwarmLedger(path=str(tmp_path / "tm_test.db"))
    tm = SwarmTimeMachine(r.ledger)
    return r, tm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_replay_from_timestamp_returns_subset(router_and_tm):
    router, tm = router_and_tm
    router.route({"task": "t1", "context": {}})
    router.route({"task": "t2", "context": {}})
    router.route({"task": "t3", "context": {}})

    all_events = router.ledger.all_events()
    assert len(all_events) == 3

    # Replay from the second event's timestamp
    pivot_ts = all_events[1]["timestamp"]
    slice_ = tm.replay_from(pivot_ts)
    assert len(slice_) >= 2  # events 2 and 3


def test_fork_produces_isolated_snapshot(router_and_tm):
    router, tm = router_and_tm
    router.route({"task": "audit", "context": {"v": 1}})
    router.route({"task": "audit", "context": {"v": 2}})

    events = router.ledger.all_events()
    fork_a = tm.fork(events[0]["event_id"])
    fork_b = tm.fork(events[1]["event_id"])

    # Mutating fork_a must not affect fork_b
    fork_a.registry_snapshot["injected"] = "poison"
    assert "injected" not in fork_b.registry_snapshot


def test_fork_carries_correct_history_length(router_and_tm):
    router, tm = router_and_tm
    for i in range(4):
        router.route({"task": f"step_{i}", "context": {}})

    events = router.ledger.all_events()
    fork = tm.fork(events[2]["event_id"])  # fork at event index 2
    assert len(fork.events_before_fork) == 3  # events 0, 1, 2


def test_diff_detects_same_agent(router_and_tm):
    router, tm = router_and_tm
    router.route({"task": "probe", "context": {"x": 1}})
    router.route({"task": "probe", "context": {"x": 1}})

    events = router.ledger.all_events()
    delta = tm.diff(events[0]["event_id"], events[1]["event_id"])

    # Same input → same agent selected → no divergence
    assert delta["agent_a"] == delta["agent_b"]
    assert not delta["diverges_at_agent"]
    assert delta["hashes_match"]
