import importlib.util
import sys
from pathlib import Path


def _load_module(module_name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    engine_dir = module_path.parent
    if relative_path.startswith("engine-c5/") and str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_engine_fuzz_hook_writes_invariant_file(tmp_path: Path) -> None:
    module = _load_module("engine_fuzz_hook_module", "engine-c5/engine_fuzz_hook.py")
    orchestrator = module.C5Orchestrator("/tmp/target")
    orchestrator.fuzz_dir = str(tmp_path)

    forge_file = orchestrator.write_forge_invariant(["delegatecall"])

    content = Path(forge_file).read_text(encoding="utf-8")
    assert "delegatecall" in content
    assert "contract C5RealExploitTest is Test" in content


def test_cortex_ast_fractor_writes_poc_file(monkeypatch, tmp_path: Path) -> None:
    module = _load_module("cortex_ast_fractor_module", "engine-c5/cortex_ast_fractor.py")
    monkeypatch.setattr(module, "call_qwen_mcts", lambda *args, **kwargs: None)

    ok = module.process_single_mutation(1, ["flashLoan"], str(tmp_path))

    assert ok is True
    poc_path = tmp_path / "PoC_Stochastic_M1.sol"
    content = poc_path.read_text(encoding="utf-8")
    assert "flashLoan" in content
    assert "L2StochasticPoC_M1" in content


def test_submission_bridge_generates_report(tmp_path: Path, monkeypatch) -> None:
    module = _load_module("submission_bridge_module", "cortex-core/submission_bridge.py")
    bridge = module.SubmissionBridge(watch_dir=str(tmp_path))
    reports_dir = tmp_path / "reports"
    monkeypatch.chdir(tmp_path)

    report_path = bridge.generate_report("demo", "contract Demo {}", "PASS")

    report_file = Path(report_path)
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "CORTEX VULNERABILITY REPORT: demo" in content
    assert "contract Demo {}" in content
