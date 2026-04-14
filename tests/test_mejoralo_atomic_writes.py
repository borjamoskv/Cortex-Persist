from __future__ import annotations

import inspect
import re
from pathlib import Path

from types import SimpleNamespace

from cortex.extensions.mejoralo import heal


class _DummyConsole:
    def print(self, *_args, **_kwargs):
        return None


def test_mejoralo_heal_module_has_no_direct_writes() -> None:
    source = inspect.getsource(heal)

    assert ".write_text(" not in source
    assert re.search(r"\bopen\([^\\n]*,\s*[\"']w[\"']", source) is None


def test_mejoralo_atomic_write_helper_is_atomic(tmp_path: Path) -> None:
    target = tmp_path / "patched.py"
    heal._atomic_write_text(target, "first\n")
    assert target.read_text(encoding="utf-8") == "first\n"

    heal._atomic_write_text(target, "second\n")
    assert target.read_text(encoding="utf-8") == "second\n"


def test_mejoralo_delta_testing_rolls_back_on_failure(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "module.py"
    target.write_text("print('original')\n", encoding="utf-8")

    def _fail_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="nope", stderr="broken")

    monkeypatch.setattr(heal.subprocess, "run", _fail_run)

    ok = heal._run_delta_testing(
        "module.py",
        tmp_path,
        "print('original')\n",
        target,
        _DummyConsole(),
        None,
        None,
        level=1,
    )

    assert ok is False
    assert target.read_text(encoding="utf-8") == "print('original')\n"
