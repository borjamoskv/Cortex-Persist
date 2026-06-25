# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from legacy_research.ledger._verifier_checkpoints import (
    verify_checkpoints,
)
from legacy_research.ledger._verifier_events import (
    verify_events,
)
from legacy_research.ledger._verifier_io import (
    build_key_index,
    load_checkpoints,
    load_events,
    load_optional_object,
)
from legacy_research.ledger._verifier_manifest import (
    manifest_export_authority_ok,
    verify_manifest,
)
from legacy_research.ledger.public_verifier_utils import (
    _load_json_object,
    _sha256_file,
)
from legacy_research.utils.canonical import canonical_json, compute_tx_hash

PUBLIC_V1_STRICT = "public-v1-strict"
LEGACY_V0 = "legacy-v0"
REPORT_GUARANTEES = (
    "integrity_verified",
    "origin_authenticity_verified",
    "authority_verified",
    "replay_consistency_verified",
    "temporal_consistency_verified",
    "online_freshness_verified",
    "completeness_verified",
    "truth_verified",
)
LEGACY_REQUIRED_FIELDS = frozenset(
    {"profile", "prev_hash", "project", "action", "detail", "timestamp", "expected_hash"}
)

ResultCode = Literal[
    "VALID_FULL_STRICT",
    "VALID_WITH_LIMITATIONS",
    "VALID_INTEGRITY_ONLY",
    "INVALID",
]


@dataclass(frozen=True)
class VerificationInput:
    export_dir: Path
    events_path: Path
    manifest_path: Path
    public_keys_path: Path
    key_events_path: Path
    schema_path: Path
    verification_profile_path: Path
    checkpoints_path: Path | None = None

    @staticmethod
    def from_export_dir(export_dir: str | Path) -> VerificationInput:
        root = Path(export_dir)
        return VerificationInput(
            export_dir=root,
            events_path=root / "events.jsonl",
            manifest_path=root / "manifest.json",
            public_keys_path=root / "public-keys.json",
            key_events_path=root / "key-events.jsonl",
            schema_path=root / "schema.json",
            verification_profile_path=root / "verification-profile.json",
            checkpoints_path=root / "checkpoints.jsonl",
        )


def verify_export(path: str | Path) -> dict[str, Any]:
    """Verify an exported public ledger package without SQLite, network, or runtime trust."""
    target = Path(path)
    if target.is_file():
        return _LegacyVectorVerifier([target]).verify()
    if _looks_like_legacy_vector_dir(target):
        return _LegacyVectorVerifier(sorted(target.glob("*.json"))).verify()
    return _PublicLedgerVerifier(VerificationInput.from_export_dir(target)).verify()


class _LegacyVectorVerifier:
    def __init__(self, vector_paths: Sequence[Path]) -> None:
        self.vector_paths = list(vector_paths)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.hashes: list[str] = []
        self.artifacts: dict[str, str | None] = {}

    def verify(self) -> dict[str, Any]:
        if not self.vector_paths:
            self.errors.append("legacy_vector_missing")
        for path in self.vector_paths:
            self._verify_vector(path)
        guarantees = dict.fromkeys(REPORT_GUARANTEES, False)
        guarantees["integrity_verified"] = not self.errors and bool(self.hashes)
        guarantees["truth_verified"] = False
        guarantees["online_freshness_verified"] = False
        errors = sorted(set(self.errors))
        warnings = sorted(set(self.warnings))
        return {
            "profile": LEGACY_V0,
            "result": "INVALID" if errors else "VALID_INTEGRITY_ONLY",
            "guarantees": guarantees,
            "counts": {
                "vectors": len(self.hashes),
                "errors": len(errors),
                "warnings": len(warnings),
            },
            "artifacts": dict(sorted(self.artifacts.items())),
            "event_hashes": list(self.hashes),
            "errors": errors,
            "warnings": warnings,
        }

    def _verify_vector(self, path: Path) -> None:
        self.artifacts[path.name] = _sha256_file(path) if path.exists() else None
        value = _load_json_object(path, self.errors)
        if value is None:
            return
        missing = sorted(LEGACY_REQUIRED_FIELDS - value.keys())
        if missing:
            self.errors.append(
                f"legacy_vector_missing_required_fields:{path.name}:{','.join(missing)}"
            )
            return
        if value.get("profile") != LEGACY_V0:
            self.errors.append(
                f"legacy_vector_profile_unsupported:{path.name}:{value.get('profile')}"
            )
            return
        try:
            detail_json = canonical_json(value["detail"])
            actual_hash = compute_tx_hash(
                str(value["prev_hash"]),
                str(value["project"]),
                str(value["action"]),
                detail_json,
                str(value["timestamp"]),
            )
        except Exception as exc:
            self.errors.append(f"legacy_vector_hash_error:{path.name}:{exc.__class__.__name__}")
            return
        self.hashes.append(actual_hash)
        if actual_hash != value.get("expected_hash"):
            self.errors.append(f"legacy_vector_hash_mismatch:{path.name}")


class _PublicLedgerVerifier:
    def __init__(self, paths: VerificationInput) -> None:
        self.paths = paths
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.events: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.key_registry: dict[str, Any] | None = None
        self.key_index: dict[str, dict[str, Any]] = {}
        self.manifest: dict[str, Any] | None = None
        self.event_hashes: list[str] = []
        self.guarantees: dict[str, bool] = dict.fromkeys(REPORT_GUARANTEES, False)

    def verify(self) -> dict[str, Any]:
        self.events = load_events(self)
        self.checkpoints = load_checkpoints(self)
        self.key_registry = load_optional_object(
            self,
            self.paths.public_keys_path,
            missing_error="public_keys_missing",
        )
        if self.key_registry is not None:
            self.key_index = build_key_index(self, self.key_registry)
        self.manifest = load_optional_object(
            self,
            self.paths.manifest_path,
            missing_warning="manifest_missing",
        )

        verify_events(self)
        verify_manifest(self)
        verify_checkpoints(self)
        self._finalize_guarantees()
        return self._report()

    def _finalize_guarantees(self) -> None:
        self.guarantees["online_freshness_verified"] = False
        self.guarantees["truth_verified"] = False

        if self.manifest is not None and self.guarantees["completeness_verified"]:
            self.guarantees["authority_verified"] = self.guarantees[
                "authority_verified"
            ] and manifest_export_authority_ok(self)

    def _report(self) -> dict[str, Any]:
        errors = sorted(set(self.errors))
        warnings = sorted(set(self.warnings))
        result = _result_code(self.guarantees, errors)
        return {
            "profile": PUBLIC_V1_STRICT,
            "result": result,
            "guarantees": {name: bool(self.guarantees[name]) for name in REPORT_GUARANTEES},
            "counts": {
                "events": len(self.events),
                "errors": len(errors),
                "warnings": len(warnings),
            },
            "artifacts": self._artifact_hashes(),
            "event_hashes": list(self.event_hashes),
            "errors": errors,
            "warnings": warnings,
        }

    def _artifact_hashes(self) -> dict[str, str | None]:
        artifacts = {
            "events.jsonl": self.paths.events_path,
            "manifest.json": self.paths.manifest_path,
            "public-keys.json": self.paths.public_keys_path,
            "key-events.jsonl": self.paths.key_events_path,
            "schema.json": self.paths.schema_path,
            "verification-profile.json": self.paths.verification_profile_path,
        }
        return {
            artifact_name: _sha256_file(path) if path.exists() else None
            for artifact_name, path in artifacts.items()
        }


def _result_code(guarantees: Mapping[str, bool], errors: Sequence[str]) -> ResultCode:
    if errors:
        return "INVALID"
    required_offline_guarantees = (
        "integrity_verified",
        "origin_authenticity_verified",
        "authority_verified",
        "replay_consistency_verified",
        "temporal_consistency_verified",
        "completeness_verified",
    )
    if all(guarantees[name] for name in required_offline_guarantees):
        return "VALID_FULL_STRICT"
    return "VALID_WITH_LIMITATIONS"


def _looks_like_legacy_vector_dir(path: Path) -> bool:
    if not path.is_dir() or (path / "events.jsonl").exists():
        return False
    return any(child.name.startswith("legacy_v0_vector_") for child in path.glob("*.json"))
