import importlib.util
import sys
from pathlib import Path


def _load_module(module_name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    if str(module_path.parent) not in sys.path:
        sys.path.insert(0, str(module_path.parent))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_remediator_applies_patch_atomically(tmp_path: Path) -> None:
    module = _load_module("remediator_module", "cortex-core/remediator.py")
    target = tmp_path / "target.py"
    target.write_text("while self.is_running:\n    pass\n", encoding="utf-8")

    surgeon = module.SovereignSurgeon(str(target), "HOT_LOOP")

    changed = surgeon.apply_patch("HOT_LOOP_REFACTOR")

    assert changed is True
    content = target.read_text(encoding="utf-8")
    assert "# AUTO_THROTTLE_V6" in content


def test_skill_compiler_main_writes_compiled_skill_and_registry(tmp_path: Path) -> None:
    module = _load_module("skill_compiler_module", "cortex-core/skill_compiler.py")
    skills_dir = tmp_path / "skills"
    compiled_dir = tmp_path / "compiled"
    skill_dir = skills_dir / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo description\n---\nBody text\n",
        encoding="utf-8",
    )

    module.SKILLS_DIR = str(skills_dir)
    module.TARGET_DIR = str(compiled_dir)

    module.main()

    compiled_file = compiled_dir / "demo_skill.py"
    registry_file = compiled_dir / "__init__.py"
    assert compiled_file.exists()
    assert registry_file.exists()
    assert "Demo description" in compiled_file.read_text(encoding="utf-8")
    assert "demo_skill" in registry_file.read_text(encoding="utf-8")


def test_cortex_chaos_fuzzer_crystallizes_harness_files(tmp_path: Path) -> None:
    module = _load_module("cortex_chaos_fuzzer_module", "engine-c5/cortex_chaos_fuzzer.py")

    ok = module.crystallize_harness(str(tmp_path))

    assert ok is True
    assert (tmp_path / "foundry.toml").exists()
    assert (tmp_path / "src" / "Target.sol").exists()
    assert (tmp_path / "test" / "ChaosInvariant.t.sol").exists()
