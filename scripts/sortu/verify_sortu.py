from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


class VerificationError(RuntimeError):
    """Raised when a Sortu skill does not satisfy the tripartite contract."""


_MANDATORY_SCHEMA_PROPERTIES = frozenset({"intent", "causal_parent", "requested_by"})
_MANDATORY_STATES = frozenset({"ACTIVE", "ABORTED", "PURGED", "QUARANTINED", "TOMBSTONED"})


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(skill_dir: Path, name: str) -> Path:
    path = skill_dir / name
    if not path.is_file():
        raise VerificationError(f"{name} is required")
    return path


def _verify_schema(path: Path) -> None:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"schema.json invalid JSON: {exc}") from exc

    if not isinstance(schema, dict):
        raise VerificationError("schema.json incomplete")

    required_keys = {"$schema", "title", "type", "required", "properties"}
    if not required_keys.issubset(schema):
        raise VerificationError("schema.json incomplete")
    if schema["type"] != "object":
        raise VerificationError("schema.json must declare type='object'")
    if not isinstance(schema["required"], list) or not isinstance(schema["properties"], dict):
        raise VerificationError("schema.json incomplete")

    declared_required = set(schema["required"])
    declared_properties = set(schema["properties"])
    missing = _MANDATORY_SCHEMA_PROPERTIES - declared_required - declared_properties
    if missing:
        names = ", ".join(sorted(missing))
        raise VerificationError(f"schema.json missing mandatory property: {names}")


def _verify_policy(path: Path) -> None:
    try:
        policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise VerificationError(f"policy.yaml invalid YAML: {exc}") from exc

    if not isinstance(policy, dict):
        raise VerificationError("policy.yaml incomplete")

    states = policy.get("states")
    if not isinstance(states, list):
        raise VerificationError("policy.yaml states must be a list")

    missing_states = _MANDATORY_STATES - {str(state) for state in states}
    if missing_states:
        names = ", ".join(sorted(missing_states))
        raise VerificationError(f"policy.yaml missing mandatory state: {names}")

    if not isinstance(policy.get("abort_reasons"), dict):
        raise VerificationError("policy.yaml incomplete")

    artifacts = policy.get("required_artifacts")
    if not isinstance(artifacts, list) or len(artifacts) < 3:
        raise VerificationError("policy.yaml incomplete")

    artifact_paths = {
        str(item.get("path"))
        for item in artifacts
        if isinstance(item, dict) and item.get("path") is not None
    }
    required = {"SKILL.md", "schema.json", "verify_*.py"}
    if not required.issubset(artifact_paths):
        raise VerificationError("policy.yaml incomplete")


def verify_tripartite(skill_dir: str | Path) -> dict[str, Any]:
    """Verify a Sortu skill directory and return artifact hashes."""
    root = Path(skill_dir)
    if not root.is_dir():
        raise VerificationError(f"skill directory not found: {root}")

    skill_md = _require_file(root, "SKILL.md")
    schema_json = _require_file(root, "schema.json")
    policy_yaml = _require_file(root, "policy.yaml")
    verify_files = sorted(path for path in root.glob("verify_*.py") if path.is_file())
    if not verify_files:
        raise VerificationError("verify_*.py is required")

    _verify_schema(schema_json)
    _verify_policy(policy_yaml)

    artifact_hashes = {
        "SKILL.md": _sha256_file(skill_md),
        "schema.json": _sha256_file(schema_json),
        "policy.yaml": _sha256_file(policy_yaml),
    }
    artifact_hashes.update({path.name: _sha256_file(path) for path in verify_files})

    return {
        "status": "PASS",
        "tripartite": True,
        "artifact_hashes": artifact_hashes,
    }
