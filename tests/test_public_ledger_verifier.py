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
    assert report["result"] == "VALID_FULL_STRICT"
    assert report["result"] == expected["result"]
    assert report["guarantees"] == expected["guarantees"]
    assert report["counts"] == {"events": 1, "errors": 0, "warnings": 0}
    assert report["event_hashes"] == [
        "518375b3ebdb916e0a779eb2baa6c9fcfbe4ae246a18eda9b4dfad0f32d2d59b"
    ]
    assert report["guarantees"]["truth_verified"] is False
    assert report["guarantees"]["online_freshness_verified"] is False


def test_verify_legacy_v0_vector_returns_integrity_only() -> None:
    report = verify_export(FIXTURES / "legacy_v0_vector_1.json")

    assert report["profile"] == "legacy-v0"
    assert report["result"] == "VALID_INTEGRITY_ONLY"
    assert report["guarantees"]["integrity_verified"] is True
    assert report["guarantees"]["truth_verified"] is False
    assert report["errors"] == []


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
    assert report["guarantees"]["truth_verified"] is False
    assert report["warnings"] == ["manifest_missing"]
    assert report["errors"] == []


def test_verify_export_rejects_missing_nonce_strict_event() -> None:
    report = verify_export(MUTATIONS / "missing_nonce")

    assert report["result"] == "INVALID"
    assert report["guarantees"]["integrity_verified"] is False
    assert "event_missing_required_fields:1:nonce" in report["errors"]


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


def test_verify_export_rejects_chain_break(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    event = json.loads((export_dir / "events.jsonl").read_text(encoding="utf-8"))
    event["prev_hash"] = "not-the-previous-hash"
    (export_dir / "events.jsonl").write_text(json.dumps(event), encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert "event_chain_break:1:expected:GENESIS" in report["errors"]


def test_verify_export_rejects_actor_without_action_permission(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    registry_path = export_dir / "public-keys.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["keys"][0]["permissions"] = ["ledger.read"]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert "event_actor_key_permission_denied:evt_01HX0000000000000000000000" in report["errors"]


def test_verify_export_accepts_rotated_historical_actor_key_without_manifest(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    (export_dir / "manifest.json").unlink()
    registry_path = export_dir / "public-keys.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["keys"][0]["status"] = "revoked"
    registry["keys"][0]["valid_until"] = "2026-06-01T00:00:00Z"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "VALID_WITH_LIMITATIONS"
    assert report["guarantees"]["authority_verified"] is True
    assert report["guarantees"]["origin_authenticity_verified"] is True
    assert not any(error.startswith("event_key_") for error in report["errors"])


def test_verify_export_rejects_revoked_key_for_future_event_without_manifest(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    (export_dir / "manifest.json").unlink()
    registry_path = export_dir / "public-keys.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["keys"][0]["status"] = "revoked"
    registry["keys"][0]["valid_until"] = "2026-01-02T00:00:00Z"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert report["guarantees"]["authority_verified"] is False
    assert "event_key_outside_validity:1" in report["errors"]


def test_verify_export_rejects_manifest_file_hash_mismatch(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    (export_dir / "schema.json").write_text('{"tampered":true}', encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert "manifest_file_hash_mismatch:schema_file_sha256" in report["errors"]


def test_verify_export_rejects_duplicate_event_ids_and_nonces(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    event_line = (STRICT / "events.jsonl").read_text(encoding="utf-8")
    (export_dir / "events.jsonl").write_text(event_line + event_line, encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert "event_replay_duplicate_event_id:evt_01HX0000000000000000000000" in report["errors"]
    assert "event_replay_duplicate_nonce:nonce_test_vector_0000000000000001" in report["errors"]


def test_verify_export_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    shutil.copytree(STRICT, export_dir)
    event_line = (STRICT / "events.jsonl").read_text(encoding="utf-8")
    event_line = event_line.replace(
        '"nonce":"nonce_test_vector_0000000000000001"',
        '"nonce":"first","nonce":"nonce_test_vector_0000000000000001"',
        1,
    )
    (export_dir / "events.jsonl").write_text(event_line, encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert any("duplicate JSON key: nonce" in error for error in report["errors"])


def test_verify_ledger_export_cli_exit_codes_and_deterministic_json(tmp_path: Path) -> None:
    runner = CliRunner()

    strict_first = runner.invoke(cli, ["verify-ledger-export", str(STRICT)])
    strict_second = runner.invoke(cli, ["verify-ledger-export", str(STRICT)])
    assert strict_first.exit_code == 0
    assert strict_first.output == strict_second.output
    assert json.loads(strict_first.output)["result"] == "VALID_FULL_STRICT"

    legacy = runner.invoke(
        cli,
        ["verify-ledger-export", str(FIXTURES / "legacy_v0_vector_1.json")],
    )
    assert legacy.exit_code == 6
    assert json.loads(legacy.output)["result"] == "VALID_INTEGRITY_ONLY"

    limited_dir = tmp_path / "limited"
    shutil.copytree(STRICT, limited_dir)
    (limited_dir / "manifest.json").unlink()
    limited = runner.invoke(cli, ["verify-ledger-export", str(limited_dir)])
    assert limited.exit_code == 6
    assert json.loads(limited.output)["result"] == "VALID_WITH_LIMITATIONS"

    invalid = runner.invoke(cli, ["verify-ledger-export", str(MUTATIONS / "tampered_detail")])
    assert invalid.exit_code == 1
    assert json.loads(invalid.output)["result"] == "INVALID"
