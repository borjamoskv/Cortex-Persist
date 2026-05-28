from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


class VerificationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise VerificationError(f"Missing required artifact: {label}")


def _validate_schema(schema_path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError("schema.json invalid JSON") from exc

    required_keys = {"$schema", "title", "type", "required", "properties"}
    if not required_keys.issubset(raw):
        raise VerificationError("schema.json incomplete")
    if raw["type"] != "object":
        raise VerificationError("schema.json must declare type='object'")

    mandatory_props = {"intent", "causal_parent", "requested_by"}
    if not mandatory_props.issubset(set(raw.get("required", []))):
        raise VerificationError("schema.json missing mandatory property in required")
    if not mandatory_props.issubset(set((raw.get("properties") or {}).keys())):
        raise VerificationError("schema.json missing mandatory property definition")
    return raw


def _validate_policy(policy_path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise VerificationError("policy.yaml invalid YAML") from exc

    if not isinstance(raw, dict):
        raise VerificationError("policy.yaml incomplete")
    states = raw.get("states")
    if not isinstance(states, list) or not states:
        raise VerificationError("policy.yaml states must be a list")
    if "ACTIVE" not in states:
        raise VerificationError("policy.yaml states must include ACTIVE")
    return raw


def verify_tripartite(skill_dir: str | Path) -> dict[str, Any]:
    root = Path(skill_dir)
    if not root.exists():
        raise VerificationError(f"{root} not found")

    skill_md = root / "SKILL.md"
    schema_json = root / "schema.json"
    policy_yaml = root / "policy.yaml"

    _require_file(skill_md, "SKILL.md")
    _require_file(schema_json, "schema.json")
    _require_file(policy_yaml, "policy.yaml")

    verifier_files = sorted(root.glob("verify_*.py"))
    if not verifier_files:
        raise VerificationError("Missing required artifact: verify_*.py")

    _validate_schema(schema_json)
    _validate_policy(policy_yaml)

    artifact_hashes = {
        "SKILL.md": _sha256(skill_md),
        "schema.json": _sha256(schema_json),
        "policy.yaml": _sha256(policy_yaml),
    }
    for path in verifier_files:
        artifact_hashes[path.name] = _sha256(path)

    return {
        "status": "PASS",
        "tripartite": True,
        "artifact_hashes": artifact_hashes,
    }
