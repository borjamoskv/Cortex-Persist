"""Tests for verify_sortu.py — Tripartite mechanical verification."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_scripts = Path.home() / ".gemini" / "antigravity" / "skills" / "Sortu" / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from verify_sortu import VerificationError, verify_tripartite


def _write_valid_skill(skill_dir: Path) -> None:
    """Create a minimal valid skill directory."""
    (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: test skill\n---\n# Test\n")
    (skill_dir / "schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Test",
                "type": "object",
                "required": ["intent", "causal_parent", "requested_by"],
                "properties": {
                    "intent": {"type": "string"},
                    "causal_parent": {"type": ["string", "null"]},
                    "requested_by": {"type": "string"},
                },
            }
        )
    )
    (skill_dir / "policy.yaml").write_text(
        "states:\n  - ACTIVE\n  - ABORTED\n"
        "abort_reasons:\n  MISSING: missing\n"
        "required_artifacts:\n"
        "  - path: SKILL.md\n    required: true\n"
        "  - path: schema.json\n    required: true\n"
        "  - path: 'verify_*.py'\n    required: true\n"
    )
    (skill_dir / "verify_test.py").write_text("# verifier\n")


class TestValidSkill:
    def test_pass_on_valid_tripartite(self, tmp_path):
        _write_valid_skill(tmp_path)
        result = verify_tripartite(tmp_path)
        assert result["status"] == "PASS"
        assert result["tripartite"] is True
        assert "SKILL.md" in result["artifact_hashes"]
        assert "schema.json" in result["artifact_hashes"]
        assert "policy.yaml" in result["artifact_hashes"]

    def test_hashes_are_hex(self, tmp_path):
        _write_valid_skill(tmp_path)
        result = verify_tripartite(tmp_path)
        for _name, h in result["artifact_hashes"].items():
            assert len(h) == 64  # SHA-256 hex
            int(h, 16)  # Must be valid hex


class TestMissingFiles:
    def test_missing_skill_md(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "SKILL.md").unlink()
        with pytest.raises(VerificationError, match="SKILL.md"):
            verify_tripartite(tmp_path)

    def test_missing_schema(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "schema.json").unlink()
        with pytest.raises(VerificationError, match="schema.json"):
            verify_tripartite(tmp_path)

    def test_missing_policy(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "policy.yaml").unlink()
        with pytest.raises(VerificationError, match="policy.yaml"):
            verify_tripartite(tmp_path)

    def test_missing_verify_file(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "verify_test.py").unlink()
        with pytest.raises(VerificationError, match="verify_"):
            verify_tripartite(tmp_path)


class TestInvalidSchema:
    def test_invalid_json(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "schema.json").write_text("{not valid json")
        with pytest.raises(VerificationError, match="invalid JSON"):
            verify_tripartite(tmp_path)

    def test_missing_required_keys(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "schema.json").write_text(json.dumps({"title": "x"}))
        with pytest.raises(VerificationError, match="incomplete"):
            verify_tripartite(tmp_path)

    def test_wrong_type(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "schema.json").write_text(
            json.dumps(
                {
                    "$schema": "x",
                    "title": "x",
                    "type": "array",
                    "required": ["a"],
                    "properties": {"a": {}},
                }
            )
        )
        with pytest.raises(VerificationError, match="type='object'"):
            verify_tripartite(tmp_path)

    def test_missing_mandatory_properties(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "schema.json").write_text(
            json.dumps(
                {
                    "$schema": "x",
                    "title": "x",
                    "type": "object",
                    "required": ["foo"],
                    "properties": {"foo": {}},
                }
            )
        )
        with pytest.raises(VerificationError, match="mandatory property"):
            verify_tripartite(tmp_path)


class TestInvalidPolicy:
    def test_invalid_yaml(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "policy.yaml").write_text(": : invalid")
        with pytest.raises(VerificationError, match="invalid YAML"):
            verify_tripartite(tmp_path)

    def test_missing_states(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "policy.yaml").write_text(
            "abort_reasons:\n  X: x\nrequired_artifacts:\n"
            "  - path: a\n  - path: b\n  - path: c\n"
        )
        with pytest.raises(VerificationError, match="Missing keys"):
            verify_tripartite(tmp_path)

    def test_states_missing_active(self, tmp_path):
        _write_valid_skill(tmp_path)
        (tmp_path / "policy.yaml").write_text(
            "states:\n  - DRAFT\n  - ABORTED\n  - FORGED\n"
            "abort_reasons:\n  X: x\n"
            "required_artifacts:\n  - path: a\n  - path: b\n  - path: c\n"
        )
        # ACTIVE is missing → should fail
        with pytest.raises(VerificationError, match="ACTIVE"):
            verify_tripartite(tmp_path)


class TestNonexistentDir:
    def test_missing_dir_raises(self):
        with pytest.raises(VerificationError, match="not found"):
            verify_tripartite(Path("/nonexistent/path/xyz"))
