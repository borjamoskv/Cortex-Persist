from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

from click.testing import CliRunner

import cortex.cli.agent_cmds as agent_cmds
import cortex.cli.architect_cmds as architect_cmds
import cortex.cli.apotheosis_cmds as apotheosis_cmds
import cortex.cli.common as cli_common
import cortex.cli.autorouter_cmds as autorouter_cmds
import cortex.cli.bibliotecario_cmds as bibliotecario_cmds
import cortex.cli.heal_cmds as heal_cmds
import cortex.cli.mejoralo_cmds as mejoralo_cmds
import cortex.cli.notebooklm_cmds as notebooklm_cmds
import cortex.cli.niche_cmds as niche_cmds
import cortex.cli.prompt_cmds as prompt_cmds
import cortex.cli.relay_daemon as relay_daemon
import cortex.cli.relay_server as relay_server
import cortex.cli.scraper_cmds as scraper_cmds
import cortex.cli.sync_cmds as sync_cmds
import cortex.cli.swarm_cmds as swarm_cmds


class _FakeFact:
    def __init__(self, project: str, fact_type: str, content: str, confidence: float = 0.9) -> None:
        self.project = project
        self.fact_type = fact_type
        self.content = content
        self.confidence = confidence


class _EmptyFrame:
    empty = True


def test_notebooklm_digest_command_writes_output(monkeypatch, tmp_path: Path) -> None:
    async def _facts():
        return [_FakeFact("demo", "decision", "Use RRF")]

    monkeypatch.setattr(notebooklm_cmds, "_get_engine_active_facts", _facts)
    monkeypatch.setattr(notebooklm_cmds, "_format_fact_obj", lambda fact: fact.content)
    monkeypatch.setattr(notebooklm_cmds, "_get_entities_and_relations", lambda: (_EmptyFrame(), []))
    monkeypatch.setattr(notebooklm_cmds, "_sovereign_signature", lambda: "SOVEREIGN")

    out_path = tmp_path / "digest.md"
    result = CliRunner().invoke(
        notebooklm_cmds.notebooklm_cmds,
        ["digest", "--output", str(out_path)],
    )

    assert result.exit_code == 0
    assert out_path.exists()
    assert "Use RRF" in out_path.read_text(encoding="utf-8")


def test_notebooklm_fragment_command_writes_domain_file(monkeypatch, tmp_path: Path) -> None:
    async def _facts():
        return [_FakeFact("demo", "knowledge", "Domain note")]

    monkeypatch.setattr(notebooklm_cmds, "_get_engine_active_facts", _facts)
    monkeypatch.setattr(notebooklm_cmds, "_format_fact_obj", lambda fact: fact.content)
    monkeypatch.setattr(notebooklm_cmds, "_sovereign_signature", lambda: "SOVEREIGN")
    monkeypatch.setitem(notebooklm_cmds._PROJECT_DOMAIN, "demo", "cortex-core")

    result = CliRunner().invoke(
        notebooklm_cmds.notebooklm_cmds,
        ["fragment", "--output-dir", str(tmp_path)],
    )

    output_files = list(tmp_path.glob("cortex-core-*.md"))
    assert result.exit_code == 0
    assert len(output_files) == 1
    assert "Domain note" in output_files[0].read_text(encoding="utf-8")


def test_notebooklm_manifest_save_writes_json(tmp_path: Path) -> None:
    manifest = tmp_path / ".cortex_ingest_manifest.json"

    notebooklm_cmds._save_processed_manifest(manifest, {"b.md", "a.md"})

    assert json.loads(manifest.read_text(encoding="utf-8")) == ["a.md", "b.md"]


def test_sync_export_command_writes_output(monkeypatch, tmp_path: Path) -> None:
    class _DummyEngine:
        async def init_db(self) -> None:
            return None

        async def get_all_active_facts(self, project=None, fact_types=None):
            return [_FakeFact("demo", "knowledge", "Fact export", confidence=0.8)]

        async def close(self) -> None:
            return None

    import cortex.utils.export as export_module

    monkeypatch.setattr(sync_cmds, "get_engine", lambda db=None: _DummyEngine())
    monkeypatch.setattr(export_module, "export_facts", lambda facts, fmt: "serialized export")

    out_path = tmp_path / "export.json"
    result = CliRunner().invoke(
        cli_common.cli,
        ["export", "--db", ":memory:", "--format", "json", "--out", str(out_path)],
    )

    assert result.exit_code == 0
    assert out_path.read_text(encoding="utf-8") == "serialized export"


def test_relay_helpers_create_buffer_files(tmp_path: Path, monkeypatch) -> None:
    relay_file = tmp_path / "relay_buffer.jsonl"
    monkeypatch.setattr(relay_server, "RELAY_PATH", str(relay_file))
    monkeypatch.setattr(relay_daemon, "RELAY_BUFFER", str(relay_file))

    server_path = relay_server.ensure_relay_buffer()
    daemon_path = relay_daemon.ensure_relay_buffer()

    assert server_path == relay_file
    assert daemon_path == relay_file
    assert relay_file.exists()


def test_cli_modules_no_direct_write_text_or_open_writes() -> None:
    open_write_pattern = re.compile(r"\bopen\([^)]*,\s*[\"']w")
    notebooklm_source = inspect.getsource(notebooklm_cmds)
    sync_source = inspect.getsource(sync_cmds)
    relay_server_source = inspect.getsource(relay_server)
    relay_daemon_source = inspect.getsource(relay_daemon)
    agent_source = inspect.getsource(agent_cmds)
    apotheosis_source = inspect.getsource(apotheosis_cmds)
    architect_source = inspect.getsource(architect_cmds)
    autorouter_source = inspect.getsource(autorouter_cmds)
    bibliotecario_source = inspect.getsource(bibliotecario_cmds)
    heal_source = inspect.getsource(heal_cmds)
    mejoralo_source = inspect.getsource(mejoralo_cmds)
    niche_source = inspect.getsource(niche_cmds)
    prompt_source = inspect.getsource(prompt_cmds)
    scraper_source = inspect.getsource(scraper_cmds)
    swarm_source = inspect.getsource(swarm_cmds)

    assert ".write_text(" not in notebooklm_source
    assert ".write_text(" not in sync_source
    assert ".write_text(" not in agent_source
    assert ".write_text(" not in apotheosis_source
    assert ".write_text(" not in architect_source
    assert ".write_text(" not in autorouter_source
    assert ".write_text(" not in bibliotecario_source
    assert ".write_text(" not in heal_source
    assert ".write_text(" not in mejoralo_source
    assert ".write_text(" not in niche_source
    assert ".write_text(" not in prompt_source
    assert ".write_text(" not in scraper_source
    assert ".write_text(" not in swarm_source

    assert 'with open(RELAY_PATH, "w")' not in relay_server_source
    assert 'aiofiles.open(RELAY_BUFFER, "w")' not in relay_daemon_source
    assert open_write_pattern.search(apotheosis_source) is None
    assert open_write_pattern.search(agent_source) is None
    assert open_write_pattern.search(architect_source) is None
    assert open_write_pattern.search(autorouter_source) is None
    assert open_write_pattern.search(bibliotecario_source) is None
    assert open_write_pattern.search(heal_source) is None
    assert open_write_pattern.search(mejoralo_source) is None
    assert open_write_pattern.search(niche_source) is None
    assert open_write_pattern.search(prompt_source) is None
    assert open_write_pattern.search(scraper_source) is None
    assert open_write_pattern.search(swarm_source) is None
