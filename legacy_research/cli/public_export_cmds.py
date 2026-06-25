# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import click
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cortex.cli.common import cli
from legacy_research.ledger.public_export import (
    ExportAuthority,
    write_public_ledger_export,
)
from legacy_research.ledger.public_verifier_utils import _loads_json_strict


@cli.command("export-ledger")
@click.argument("events_jsonl", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("export_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option(
    "--public-keys",
    "public_keys_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--export-id", required=True)
@click.option("--tenant-id", required=True)
@click.option("--stream-id", required=True)
@click.option("--export-authority-key-id", required=True)
@click.option("--export-authority-actor-id", required=True)
@click.option(
    "--export-authority-private-key-seed",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a base64url-encoded raw Ed25519 private key seed.",
)
@click.option("--created-at")
@click.option("--purpose", default="forensic_ledger_export", show_default=True)
@click.option("--environment", default="test", show_default=True)
@click.option("--include-verification-report", is_flag=True)
def export_ledger(
    events_jsonl: Path,
    export_dir: Path,
    public_keys_path: Path,
    export_id: str,
    tenant_id: str,
    stream_id: str,
    export_authority_key_id: str,
    export_authority_actor_id: str,
    export_authority_private_key_seed: Path,
    created_at: str | None,
    purpose: str,
    environment: str,
    include_verification_report: bool,
) -> None:
    """Write a signed public ledger export package from public-v1 JSONL."""
    events = _load_events_jsonl(events_jsonl)
    public_keys = _load_public_keys(public_keys_path)
    private_key = Ed25519PrivateKey.from_private_bytes(
        _decode_b64url_file(export_authority_private_key_seed)
    )

    result = write_public_ledger_export(
        events=events,
        export_dir=export_dir,
        public_keys=public_keys,
        export_authority=ExportAuthority(
            key_id=export_authority_key_id,
            actor_id=export_authority_actor_id,
            private_key=private_key,
            environment=environment,
        ),
        export_id=export_id,
        tenant_id=tenant_id,
        stream_id=stream_id,
        purpose=purpose,
        environment=environment,
        created_at=created_at,
        include_verification_report=include_verification_report,
    )
    click.echo(
        json.dumps(
            {
                "export_dir": str(result.export_dir),
                "manifest_hash": result.manifest_hash,
                "verification_result": result.verification_result,
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_events_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        value = _loads_json_strict(line)
        if not isinstance(value, dict):
            raise click.ClickException(f"events_jsonl_non_object:{line_number}")
        events.append(value)
    if not events:
        raise click.ClickException("events_jsonl_empty")
    return events


def _load_public_keys(path: Path) -> list[dict[str, Any]]:
    value = _loads_json_strict(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        keys = value.get("keys")
    else:
        keys = value
    if not isinstance(keys, list) or not all(isinstance(key, dict) for key in keys):
        raise click.ClickException("public_keys_invalid")
    return [dict(key) for key in keys]


def _decode_b64url_file(path: Path) -> bytes:
    value = path.read_text(encoding="utf-8").strip()
    padding = "=" * (-len(value) % 4)
    seed = base64.urlsafe_b64decode(value + padding)
    if len(seed) != 32:
        raise click.ClickException("export_authority_private_key_seed_must_be_32_bytes")
    return seed
