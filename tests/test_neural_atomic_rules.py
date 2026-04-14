from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_extension_neural_default_rules_are_written_atomically() -> None:
    source = _source("cortex/extensions/agents/neural.py")
    assert "open(self._rules_path, \"w\"" not in source
    assert "_atomic_write_text(" in source


def test_root_neural_default_rules_are_written_atomically() -> None:
    source = _source("cortex/agents/neural.py")
    assert "open(self._rules_path, \"w\"" not in source
    assert "_atomic_write_text(" in source
