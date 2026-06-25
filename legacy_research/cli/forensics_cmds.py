# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

import click

from cortex.cli.common import DEFAULT_DB, cli
from cortex.forensics.evidence_bundle import (
    build_evidence_manifest,
    commit_evidence_manifest,
    dump_evidence_manifest,
    load_evidence_manifest_bytes,
    verify_evidence_commit,
    verify_evidence_manifest,
)


@click.group("forensics")
def forensics_cmds() -> None:
    """Local forensic evidence utilities."""


@forensics_cmds.command("build-manifest")
@click.argument(
    "artifacts",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=str),
)
@click.option(
    "--base-dir",
    default=".",
    show_default=True,
    type=click.Path(exists=True, file_okay=False, path_type=str),
    help="Directory used to derive manifest-relative artifact paths.",
)
@click.option("--bundle-id", required=True, help="Stable identifier for this evidence bundle.")
@click.option("--tenant-id", default="default", show_default=True, help="Tenant scope.")
@click.option("--project", default=None, help="Optional project scope.")
@click.option(
    "--profile",
    default="customer-confidential",
    show_default=True,
    help="Delivery profile recorded in the manifest.",
)
@click.option(
    "--generated-at",
    default=None,
    help="Optional ISO timestamp. Defaults to current UTC time.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False, path_type=str),
    help="Manifest JSON output path.",
)
def build_manifest_cmd(
    artifacts: tuple[str, ...],
    base_dir: str,
    bundle_id: str,
    tenant_id: str,
    project: str | None,
    profile: str,
    generated_at: str | None,
    output: str,
) -> None:
    """Build a canonical SHA-256 manifest for local evidence artifacts."""
    base = _resolve_base_dir(base_dir)
    output_path = Path(output)
    _ensure_output_does_not_overwrite_artifact(output_path, artifacts)
    artifact_bytes = _read_explicit_artifacts(base, artifacts)
    manifest = build_evidence_manifest(
        artifact_bytes,
        bundle_id=bundle_id,
        tenant_id=tenant_id,
        project=project,
        generated_at=generated_at,
        profile=profile,
    )
    _atomic_write_bytes(output_path, dump_evidence_manifest(manifest))
    _emit_status_json(
        {
            "valid": True,
            "manifest": str(output_path),
            "manifest_sha256": manifest["manifest_sha256"],
            "artifact_count": manifest["artifact_count"],
            "total_bytes": manifest["total_bytes"],
        },
        status_code=0,
    )


@forensics_cmds.command("verify-manifest")
@click.argument("manifest", type=click.Path(exists=True, dir_okay=False, path_type=str))
@click.option(
    "--base-dir",
    default=".",
    show_default=True,
    type=click.Path(exists=True, file_okay=False, path_type=str),
    help="Directory containing the manifest-listed artifact paths.",
)
def verify_manifest_cmd(manifest: str, base_dir: str) -> None:
    """Verify a canonical evidence manifest against local artifact bytes."""
    manifest_payload, artifacts, manifest_path, base = _load_manifest_and_artifacts(
        manifest, base_dir
    )
    report = verify_evidence_manifest(manifest_payload, artifacts)
    _emit_status_json(
        {
            "manifest": str(manifest_path),
            "base_dir": str(base),
            **report,
        },
        status_code=0 if report["valid"] is True else 1,
    )


@forensics_cmds.command("commit-manifest")
@click.argument("manifest", type=click.Path(exists=True, dir_okay=False, path_type=str))
@click.option(
    "--base-dir",
    default=".",
    show_default=True,
    type=click.Path(exists=True, file_okay=False, path_type=str),
    help="Directory containing the manifest-listed artifact paths.",
)
@click.option("--db", default=DEFAULT_DB, show_default=True, help="Database path.")
def commit_manifest_cmd(manifest: str, base_dir: str, db: str) -> None:
    """Verify and commit a forensic evidence manifest to the transaction ledger."""
    manifest_payload, artifacts, manifest_path, base = _load_manifest_and_artifacts(
        manifest, base_dir
    )
    result = commit_evidence_manifest(db, manifest_payload, artifacts)
    _emit_status_json(
        {
            "manifest": str(manifest_path),
            "base_dir": str(base),
            "db": db,
            **result,
        },
        status_code=0 if result["valid"] is True and result["committed"] is True else 1,
    )


@forensics_cmds.command("verify-commit")
@click.argument("manifest", type=click.Path(exists=True, dir_okay=False, path_type=str))
@click.option(
    "--base-dir",
    default=".",
    show_default=True,
    type=click.Path(exists=True, file_okay=False, path_type=str),
    help="Directory containing the manifest-listed artifact paths.",
)
@click.option("--db", default=DEFAULT_DB, show_default=True, help="Database path.")
def verify_commit_cmd(manifest: str, base_dir: str, db: str) -> None:
    """Verify a forensic manifest and its matching transaction-ledger commitment."""
    manifest_payload, artifacts, manifest_path, base = _load_manifest_and_artifacts(
        manifest, base_dir
    )
    report = verify_evidence_commit(db, manifest_payload, artifacts)
    _emit_status_json(
        {
            "manifest": str(manifest_path),
            "base_dir": str(base),
            "db": db,
            **report,
        },
        status_code=0 if report["valid"] is True else 1,
    )


def _read_explicit_artifacts(base: Path, artifacts: tuple[str, ...]) -> dict[str, bytes]:
    artifact_bytes: dict[str, bytes] = {}
    for artifact in artifacts:
        artifact_path = _resolve_under_base(Path(artifact), base, label="artifact")
        relative_path = artifact_path.relative_to(base).as_posix()
        artifact_bytes[relative_path] = artifact_path.read_bytes()
    return artifact_bytes


def _ensure_output_does_not_overwrite_artifact(output: Path, artifacts: tuple[str, ...]) -> None:
    resolved_output = output.resolve(strict=False)
    for artifact in artifacts:
        artifact_path = Path(artifact)
        if not artifact_path.exists():
            continue
        if artifact_path.resolve(strict=True) == resolved_output:
            raise click.ClickException("--output must not overwrite an evidence artifact")


def _load_manifest_and_artifacts(
    manifest: str,
    base_dir: str,
) -> tuple[dict[str, Any], dict[str, bytes], Path, Path]:
    base = _resolve_base_dir(base_dir)
    manifest_path = Path(manifest).resolve(strict=True)
    try:
        manifest_payload = load_evidence_manifest_bytes(manifest_path.read_bytes())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    artifacts: dict[str, bytes] = {}
    for relative_path in _manifest_artifact_paths(manifest_payload):
        artifact_path = _resolve_manifest_entry(base, relative_path)
        if not artifact_path.exists() or not artifact_path.is_file():
            continue
        artifacts[relative_path] = artifact_path.read_bytes()
    return manifest_payload, artifacts, manifest_path, base


def _resolve_base_dir(base_dir: str) -> Path:
    return Path(base_dir).resolve(strict=True)


def _resolve_under_base(path: Path, base: Path, *, label: str) -> Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise click.ClickException(f"{label} is outside --base-dir: {path}") from exc
    return resolved


def _resolve_manifest_entry(base: Path, relative_path: str) -> Path:
    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
        raise click.ClickException(f"manifest contains unsafe artifact path: {relative_path}")
    candidate = base.joinpath(*pure_path.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise click.ClickException(
            f"manifest artifact is outside --base-dir: {relative_path}"
        ) from exc
    return resolved


def _manifest_artifact_paths(manifest: dict[str, Any]) -> list[str]:
    entries = manifest.get("artifacts")
    if not isinstance(entries, list):
        raise click.ClickException("manifest artifacts must be a list")
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise click.ClickException("manifest artifact entries must contain string paths")
        paths.append(entry["path"])
    return paths


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(path)


def _emit_status_json(payload: dict[str, Any], *, status_code: int) -> None:
    click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    if status_code:
        raise click.exceptions.Exit(status_code)


if os.environ.get("CORTEX_ENABLE_EXPERIMENTAL_CLI", "") in ("1", "true", "True"):
    cli.add_command(forensics_cmds, name="forensics")
