import importlib.util
from pathlib import Path


def _load_swarm_manager_module():
    module_path = Path(__file__).resolve().parents[1] / "cortex" / "swarm" / "manager.py"
    spec = importlib.util.spec_from_file_location("cortex_swarm_manager_module", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_comms_actuator_spools_failed_delivery(tmp_path: Path) -> None:
    module = _load_swarm_manager_module()
    actuator = module.CommsActuator()
    actuator.SPOOL_DIR = str(tmp_path)

    actuator._attempt_smtp = lambda *args, **kwargs: (False, RuntimeError("smtp offline"))
    actuator._background_send_with_spool(
        "ops@example.com",
        "subject",
        "sealed-prompt",
        "abc123",
        "smtp.example.com",
        587,
        "user",
        "pass",
    )

    spool_file = tmp_path / "abc123.spool"
    assert spool_file.exists()
    content = spool_file.read_text(encoding="utf-8")
    assert content.startswith("HDR|ops@example.com|subject|smtp offline")
    assert content.endswith("sealed-prompt")


def test_autodidact_jit_mutates_target_file_when_forge_fails(tmp_path: Path) -> None:
    module = _load_swarm_manager_module()
    actuator = module.AutodidactJITActuator()
    target_file = tmp_path / "ValidationMitigation.t.sol"
    target_file.write_text("pragma solidity ^0.8.0;\n", encoding="utf-8")

    class DummyResult:
        returncode = 1
        stdout = ""

    original_run = module.subprocess.run
    module.subprocess.run = lambda *args, **kwargs: DummyResult()
    try:
        result = actuator.execute_task(
            "Execute autonomous_fuzzing in target repo",
            {"target_dir": str(tmp_path), "match_path": target_file.name},
        )
    finally:
        module.subprocess.run = original_run

    mutated = target_file.read_text(encoding="utf-8")
    assert result["status"] == "success"
    assert "// [CORTEX-M1] Mutación Vector Termodinámica 1" in mutated
    assert "// [CORTEX-M1] Mutación Vector Termodinámica 5" in mutated
