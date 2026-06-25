# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from cortex.cli.forensics_cmds import forensics_cmds

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_TS = "2026-05-05T00:00:00+00:00"


def _json_output(output: str) -> dict[str, object]:
    return json.loads(output)


def test_forensics_cli_build_verify_commit_round_trip(tmp_path) -> None:
    base = tmp_path / "evidence"
    artifact = base / "reports" / "summary.txt"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("customer-confidential evidence\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    db_path = tmp_path / "ledger.db"
    runner = CliRunner()

    built = runner.invoke(
        forensics_cmds,
        [
            "build-manifest",
            str(artifact),
            "--base-dir",
            str(base),
            "--bundle-id",
            "bundle-cli",
            "--tenant-id",
            "tenant-cli",
            "--project",
            "cli-project",
            "--generated-at",
            FIXED_TS,
            "--output",
            str(manifest_path),
        ],
    )
    assert built.exit_code == 0, built.output
    built_payload = _json_output(built.output)
    assert built_payload["valid"] is True
    assert built_payload["artifact_count"] == 1
    assert manifest_path.exists()

    verified = runner.invoke(
        forensics_cmds,
        ["verify-manifest", str(manifest_path), "--base-dir", str(base)],
    )
    assert verified.exit_code == 0, verified.output
    assert _json_output(verified.output)["valid"] is True

    committed = runner.invoke(
        forensics_cmds,
        ["commit-manifest", str(manifest_path), "--base-dir", str(base), "--db", str(db_path)],
    )
    assert committed.exit_code == 0, committed.output
    committed_payload = _json_output(committed.output)
    assert committed_payload["committed"] is True
    assert committed_payload["tenant_id"] == "tenant-cli"

    verified_commit = runner.invoke(
        forensics_cmds,
        ["verify-commit", str(manifest_path), "--base-dir", str(base), "--db", str(db_path)],
    )
    assert verified_commit.exit_code == 0, verified_commit.output
    assert _json_output(verified_commit.output)["valid"] is True


def test_forensics_cli_missing_artifact_exits_nonzero(tmp_path) -> None:
    base = tmp_path / "evidence"
    artifact = base / "report.txt"
    base.mkdir()
    artifact.write_text("evidence\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    runner = CliRunner()

    built = runner.invoke(
        forensics_cmds,
        [
            "build-manifest",
            str(artifact),
            "--base-dir",
            str(base),
            "--bundle-id",
            "bundle-missing",
            "--tenant-id",
            "tenant-cli",
            "--generated-at",
            FIXED_TS,
            "--output",
            str(manifest_path),
        ],
    )
    assert built.exit_code == 0, built.output

    artifact.unlink()
    verified = runner.invoke(
        forensics_cmds,
        ["verify-manifest", str(manifest_path), "--base-dir", str(base)],
    )

    assert verified.exit_code == 1
    payload = _json_output(verified.output)
    assert payload["valid"] is False
    assert {violation["type"] for violation in payload["violations"]} >= {
        "ARTIFACT_MISSING",
        "MANIFEST_TOTAL_BYTES_MISMATCH",
    }


def test_forensics_cli_build_manifest_refuses_to_overwrite_artifact(tmp_path) -> None:
    base = tmp_path / "evidence"
    artifact = base / "report.txt"
    base.mkdir()
    artifact.write_text("evidence\n", encoding="utf-8")
    original = artifact.read_bytes()
    runner = CliRunner()

    result = runner.invoke(
        forensics_cmds,
        [
            "build-manifest",
            str(artifact),
            "--base-dir",
            str(base),
            "--bundle-id",
            "bundle-overwrite",
            "--tenant-id",
            "tenant-cli",
            "--generated-at",
            FIXED_TS,
            "--output",
            str(artifact),
        ],
    )

    assert result.exit_code == 1
    assert "must not overwrite" in result.output
    assert artifact.read_bytes() == original


def test_forensics_cli_rejects_manifest_paths_outside_base(tmp_path) -> None:
    base = tmp_path / "evidence"
    base.mkdir()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {"schema": "cortex.forensics.evidence_manifest.v1", "artifacts": [{"path": "../x"}]}
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        forensics_cmds,
        ["verify-manifest", str(manifest_path), "--base-dir", str(base)],
    )

    assert result.exit_code == 1
    assert "unsafe artifact path" in result.output


def test_forensics_command_is_experimental_in_root_cli(monkeypatch) -> None:
    import importlib
    import cortex.cli.common
    import cortex.cli.forensics_cmds

    if "forensics" in cortex.cli.common.cli.commands:
        del cortex.cli.common.cli.commands["forensics"]

    import os
    if "CORTEX_ENABLE_EXPERIMENTAL_CLI" in os.environ:
        del os.environ["CORTEX_ENABLE_EXPERIMENTAL_CLI"]
    importlib.reload(cortex.cli.forensics_cmds)
    assert "forensics" not in cortex.cli.common.cli.commands

    os.environ["CORTEX_ENABLE_EXPERIMENTAL_CLI"] = "1"
    importlib.reload(cortex.cli.forensics_cmds)
    assert "forensics" in cortex.cli.common.cli.commands
