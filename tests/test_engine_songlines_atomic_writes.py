from __future__ import annotations

import inspect
import json
import re
import time
from pathlib import Path

from cortex.engine.ghost_mixin import GhostMixin
from cortex.engine.reaper import GhostReaper


def test_reaper_updates_songlines_manifest_atomically(tmp_path: Path) -> None:
    manifest = tmp_path / ".songlines"
    manifest.write_text(
        json.dumps(
            {
                "demo.py": {
                    "user.cortex.ghost.deadbeef": {
                        "timestamp": time.time() - 10_000,
                        "intent": "stale",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    reaped = GhostReaper(ttl_days=1)._reap_manifest(manifest, time.time() - 100)

    assert reaped == 1
    assert json.loads(manifest.read_text(encoding="utf-8")) == {}


def test_ghost_mixin_resolve_manifest_fallback_removes_entry(tmp_path: Path) -> None:
    source = tmp_path / "demo.py"
    source.write_text("print('demo')\n", encoding="utf-8")
    manifest = tmp_path / ".songlines"
    attr_name = "user.cortex.ghost.deadbeef"
    manifest.write_text(
        json.dumps(
            {
                source.name: {
                    attr_name: '{"id":"deadbeef","intent":"trace"}',
                }
            }
        ),
        encoding="utf-8",
    )

    GhostMixin()._resolve_manifest_fallback(source, attr_name)

    assert json.loads(manifest.read_text(encoding="utf-8")) == {}


def test_songlines_engine_modules_no_direct_manifest_writes() -> None:
    reaper_source = inspect.getsource(GhostReaper)
    ghost_source = inspect.getsource(GhostMixin)

    assert ".write_text(" not in reaper_source
    assert ".write_text(" not in ghost_source
    assert 'with open(manifest_path, "w")' not in reaper_source
    assert 'with open(manifest, "w")' not in ghost_source


def test_resonance_emitter_fallback_manifest_write(tmp_path: Path) -> None:
    from cortex.extensions.songlines.emitter import ResonanceEmitter

    target = tmp_path / "sample.py"
    target.write_text("print('sample')\n", encoding="utf-8")
    emitter = ResonanceEmitter()

    songline_file = tmp_path / ".songlines"
    emitter._fallback_embed(target, "user.cortex.ghost.test", b"abc")

    data = json.loads(songline_file.read_text(encoding="utf-8"))
    assert data["sample.py"]["user.cortex.ghost.test"] == "abc"
    assert songline_file.exists()


def test_songlines_no_direct_fallback_open_w() -> None:
    from cortex.extensions.songlines import emitter as emitter_module

    source = inspect.getsource(emitter_module.ResonanceEmitter._fallback_embed)
    assert ".write_text(" not in source
    assert re.search(r"\bopen\([^\\n]*,\s*[\"']w[\"']", source) is None
