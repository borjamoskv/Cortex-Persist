import time
import pytest

from cortex.skills.registry import SkillManifest, SkillRegistry
from cortex.memory.procedural import ProceduralMemory
from cortex.memory.metamemory import MetamemoryMonitor
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
    judgment_tot = monitor.judge_procedural_fok("code something entirely different in a new language", bad_match)
    
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
