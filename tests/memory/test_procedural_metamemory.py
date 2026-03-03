import time

import pytest

from cortex.memory.metamemory import MetamemoryMonitor
from cortex.memory.procedural import ProceduralMemory
from cortex.skills.registry import SkillManifest, SkillRegistry
from cortex.skills.router import SkillRouter


@pytest.fixture
def mock_registry(tmp_path):
    class MockRegistry(SkillRegistry):
        def __init__(self):
            super().__init__()
            self._manifests = {}

            # Add some fake skills
            self._manifests["write-code"] = SkillManifest(
                name="Write Code",
                path=tmp_path / "write_code.md",
                description="Write excellent python code",
                category="coding",
            )
            self._manifests["analyze-data"] = SkillManifest(
                name="Analyze Data",
                path=tmp_path / "analyze_data.md",
                description="Analyze pandas dataframe",
                category="data",
            )

        def search(self, intent: str):
            # Simple keyword match for testing
            intent = intent.lower()
            results = []
            for m in self._manifests.values():
                if any(w in m.name.lower() or w in m.description.lower() for w in intent.split()):
                    results.append(m)
            return results

        def get(self, name: str):
            return self._manifests.get(name)

    return MockRegistry()


def test_procedural_memory_valuation():
    pm = ProceduralMemory()

    # Simulate a highly successful fast skill
    pm.record_execution("write-code", success=True, latency_ms=50.0)
    pm.record_execution("write-code", success=True, latency_ms=45.0)

    # Simulate a failing slow skill
    pm.record_execution("analyze-data", success=False, latency_ms=1200.0)

    write_engram = pm.get_engram("write-code")
    analyze_engram = pm.get_engram("analyze-data")

    assert write_engram is not None
    assert analyze_engram is not None

    assert write_engram.success_rate > 0.8
    assert analyze_engram.success_rate < 0.5

    assert write_engram.avg_latency_ms < 100.0
    assert analyze_engram.avg_latency_ms > 200.0

    assert write_engram.striatal_value > analyze_engram.striatal_value


def test_metamemory_procedural_fok_high(mock_registry):
    monitor = MetamemoryMonitor()
    candidates = mock_registry.search("Write some python code")

    judgment = monitor.judge_procedural_fok("Write some python code", candidates)

    assert judgment.domain == "procedural"
    assert judgment.fok_score >= 0.5  # High overlap
    assert not judgment.tip_of_tongue


def test_metamemory_procedural_fok_low_or_tot(mock_registry):
    monitor = MetamemoryMonitor()

    # No match
    candidates = mock_registry.search("Bake a cake")
    judgment = monitor.judge_procedural_fok("Bake a cake", candidates)
    assert judgment.fok_score < 0.35

    # Partial match that shouldn't be confident enough
    # If there are candidates but the overlap is low, it might trigger Tip Of Tongue
    # Since search only returns if there is SOME match, we fake search returning a bad match
    bad_match = [mock_registry.get("write-code")]
    judgment_tot = monitor.judge_procedural_fok(
        "code something entirely different in a new language", bad_match
    )

    # Depending on thresholds, could be TOT
    assert judgment_tot.fok_score > 0.0


def test_skill_router_gatekeeping(mock_registry):
    router = SkillRouter(registry=mock_registry)

    # Known intent
    candidates = router.route_intent("Write python code")
    assert len(candidates) > 0
    assert candidates[0].slug == "write-code"

    # Unknown intent
    candidates_unknown = router.route_intent("Bake a chocolate cake")
    assert len(candidates_unknown) == 0  # Metamemory should block it


# ─── Permanent Engram Tests ──────────────────────────────────────────────


def test_permanent_engram_bypasses_decay(monkeypatch):
    """A permanent engram should retain full striatal value even after 90 days."""
    pm = ProceduralMemory()
    pm.record_execution("keter-omega", success=True, latency_ms=30.0, permanent=True)

    engram_fresh = pm.get_engram("keter-omega")
    assert engram_fresh is not None
    fresh_value = engram_fresh.striatal_value

    # Simulate 90 days elapsed (3× the half-life)
    fake_now = time.time() + (90 * 24 * 3600)
    monkeypatch.setattr(time, "time", lambda: fake_now)

    # Re-fetch — frozen dataclass, so striatal_value recomputes on access
    engram_aged = pm.get_engram("keter-omega")
    assert engram_aged is not None
    assert engram_aged.striatal_value == pytest.approx(fresh_value, abs=0.01)


def test_permanent_flag_propagated_on_update():
    """Once marked permanent, subsequent records without the flag must keep it."""
    pm = ProceduralMemory()
    pm.record_execution("keter-omega", success=True, latency_ms=20.0, permanent=True)

    # Second execution does NOT pass permanent=True
    pm.record_execution("keter-omega", success=True, latency_ms=25.0)

    engram = pm.get_engram("keter-omega")
    assert engram is not None
    assert engram.permanent is True, "permanent flag must be sticky (or-propagated)"
    assert engram.invocations == 2


def test_non_permanent_engram_decays(monkeypatch):
    """A normal engram should lose ~50% value after exactly one half-life (30 days)."""
    pm = ProceduralMemory()
    pm.record_execution("temp-skill", success=True, latency_ms=50.0)

    engram = pm.get_engram("temp-skill")
    assert engram is not None
    fresh_value = engram.striatal_value

    # Jump forward by exactly one half-life (30 days)
    fake_now = time.time() + (30 * 24 * 3600)
    monkeypatch.setattr(time, "time", lambda: fake_now)

    decayed_value = engram.striatal_value
    ratio = decayed_value / fresh_value
    # Should be ~0.5 (within tolerance for the frequency_bonus component)
    assert 0.4 < ratio < 0.6, f"Expected ~50% decay, got {ratio:.2%}"


def test_omega_skill_enforced_permanence(monkeypatch):
    """Omega skills must be permanent even if created with permanent=False."""
    pm = ProceduralMemory()

    # Intentionally try to create a non-permanent omega skill
    pm.record_execution("keter-omega", success=True, latency_ms=10.0, permanent=False)

    engram = pm.get_engram("keter-omega")
    assert engram is not None
    assert engram.permanent is True, "Omega skills must be permanent by design (Ω₄)"

    # Verify it doesn't decay
    fresh_value = engram.striatal_value
    fake_now = time.time() + (100 * 365 * 24 * 3600)  # 100 years later
    monkeypatch.setattr(time, "time", lambda: fake_now)

    assert engram.striatal_value == pytest.approx(fresh_value)
