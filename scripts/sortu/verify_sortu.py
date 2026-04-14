from __future__ import annotations

"""Mechanical verification of a SORTU tripartite package."""

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


MANDATORY_SCHEMA_FIELDS = {"intent", "causal_parent", "requested_by"}


class VerificationError(RuntimeError):
    """Raised when the mechanical tripartite verification fails."""


def _sha256(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _require_file(path: Path, name: str) -> None:
    if not path.exists():
        raise VerificationError(f"{name} not found")


def _validate_schema(schema_path: Path) -> None:
    try:
        payload: Any = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON in schema: {exc}") from exc

    required = payload.get("required")
    if not isinstance(required, list):
        raise VerificationError("schema.json is incomplete: required field missing or invalid")

    schema_type = payload.get("type")
    if schema_type != "object":
        raise VerificationError(f"type='object' required but schema has type={schema_type!r}")

    if not set(MANDATORY_SCHEMA_FIELDS).issubset(set(required)):
        missing = sorted(MANDATORY_SCHEMA_FIELDS - set(required))
        raise VerificationError(f"schema.json is incomplete: mandatory property missing: {', '.join(missing)}")

    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise VerificationError("schema.json is incomplete: properties must be an object")

    missing_props = sorted(MANDATORY_SCHEMA_FIELDS - set(properties.keys()))
    if missing_props:
        raise VerificationError(
            "schema.json incomplete: mandatory property missing: "
            + ", ".join(missing_props)
        )


def _validate_policy(policy_path: Path) -> None:
    try:
        payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - handled for explicit YAML errors
        raise VerificationError(f"invalid YAML in policy.yaml: {exc}") from exc

    if not isinstance(payload, dict):
        raise VerificationError("policy.yaml is incomplete: expected a mapping")

    states = payload.get("states")
    if not isinstance(states, list):
        raise VerificationError("states must be a list")
    if "ACTIVE" not in states:
        raise VerificationError("policy.yaml states must include ACTIVE")


def verify_tripartite(skill_dir: Path) -> dict[str, object]:
    """Verify a minimal SORTU skill directory and return verification metadata."""

    if not skill_dir.exists() or not skill_dir.is_dir():
        raise VerificationError(f"{skill_dir} not found")

    skill_md = skill_dir / "SKILL.md"
    schema_json = skill_dir / "schema.json"
    policy_yaml = skill_dir / "policy.yaml"

    _require_file(skill_md, "SKILL.md")
    _require_file(schema_json, "schema.json")
    _require_file(policy_yaml, "policy.yaml")

    verify_scripts = sorted(skill_dir.glob("verify_*.py"))
    if not verify_scripts:
        raise VerificationError("verify_ script missing (verify_*.py)")

    _validate_schema(schema_json)
    _validate_policy(policy_yaml)

    artifact_hashes = {
        "SKILL.md": _sha256(skill_md),
        "schema.json": _sha256(schema_json),
        "policy.yaml": _sha256(policy_yaml),
    }
    for script in verify_scripts:
        artifact_hashes[script.name] = _sha256(script)

    return {
        "status": "PASS",
        "tripartite": True,
        "artifact_hashes": artifact_hashes,
    }
