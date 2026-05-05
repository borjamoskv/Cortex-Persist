from __future__ import annotations

import json
import shutil
from pathlib import Path

from click.testing import CliRunner

from cortex.cli import cli
from cortex.ledger.public_verifier import verify_export

FIXTURES = Path(__file__).parent / "fixtures" / "ledger_verifier"
STRICT = FIXTURES / "public_v1_strict"
MUTATIONS = FIXTURES / "public_v1_strict_mutations"


def test_verify_export_returns_full_strict_report_for_public_v1_fixture() -> None:
    report = verify_export(STRICT)
    expected = json.loads((STRICT / "expected-report.json").read_text(encoding="utf-8"))

    assert report["profile"] == "public-v1-strict"
    assert report["result"] == expected["result"]
    assert report["guarantees"] == expected["guarantees"]
    assert report["counts"] == {"events": 1, "errors": 0, "warnings": 0}
    assert report["event_hashes"] == [
        "518375b3ebdb916e0a779eb2baa6c9fcfbe4ae246a18eda9b4dfad0f32d2d59b"
    ]


def test_verify_export_without_manifest_is_valid_with_limitations(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    (export_dir / "manifest.json").unlink()

    report = verify_export(export_dir)

    assert report["result"] == "VALID_WITH_LIMITATIONS"
    assert report["guarantees"]["integrity_verified"] is True
    assert report["guarantees"]["origin_authenticity_verified"] is True
    assert report["guarantees"]["authority_verified"] is True
    assert report["guarantees"]["completeness_verified"] is False
    assert report["warnings"] == ["manifest_missing"]
    assert report["errors"] == []


def test_verify_export_rejects_missing_nonce_strict_event() -> None:
    report = verify_export(MUTATIONS / "missing_nonce")

    assert report["result"] == "INVALID"
    assert report["guarantees"]["integrity_verified"] is False
    assert any(
        error.startswith("event_missing_required_fields:1:nonce") for error in report["errors"]
    )


def test_verify_export_rejects_tampered_detail_hash() -> None:
    report = verify_export(MUTATIONS / "tampered_detail")

    assert report["result"] == "INVALID"
    assert "event_hash_mismatch:evt_01HX0000000000000000000000" in report["errors"]


def test_verify_export_rejects_bad_manifest_signature(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    shutil.copyfile(
        MUTATIONS / "bad_manifest_signature" / "manifest.json",
        export_dir / "manifest.json",
    )

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert "manifest_signature_invalid:InvalidSignature" in report["errors"]


def test_verify_ledger_export_cli_emits_report_and_exit_zero_for_full_strict() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["verify-ledger-export", str(STRICT)])

    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report["result"] == "VALID_FULL_STRICT"
    assert report["guarantees"]["truth_verified"] is False


def test_verify_ledger_export_cli_exits_two_for_limitations(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    (export_dir / "manifest.json").unlink()
    runner = CliRunner()

    result = runner.invoke(cli, ["verify-ledger-export", str(export_dir)])

    assert result.exit_code == 2
    report = json.loads(result.output)
    assert report["result"] == "VALID_WITH_LIMITATIONS"


def test_verify_ledger_export_cli_exits_one_for_invalid_export() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["verify-ledger-export", str(MUTATIONS / "tampered_detail")])

    assert result.exit_code == 1
    report = json.loads(result.output)
    assert report["result"] == "INVALID"
