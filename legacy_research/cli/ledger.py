# [C5-REAL] Exergy-Maximized

import json
from pathlib import Path

import click
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, cli
from legacy_research.ledger.public_export import (
    ExportAuthority,
    public_key_record,
    write_public_ledger_export,
)
from legacy_research.ledger.public_verifier_utils import _event_hash, _event_signature_scope
from legacy_research.ledger.store import LedgerStore
from legacy_research.ledger.verifier import LedgerVerifier

console = Console()


@click.group(name="ledger")
def ledger_cmds():
    """Sovereign Ledger Operations (Wave 6: High-Performance Chaining)."""


@ledger_cmds.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--full", is_flag=True, help="Perform full cryptographic verify")
def verify_ledger(db: str, full: bool):
    """Verify hash chain integrity."""
    store = LedgerStore(db)
    verifier = LedgerVerifier(store)

    with console.status("[bold cyan]Verifying ledger integrity..."):
        result = verifier.verify_chain()

    if result["valid"]:
        console.print(
            f"[bold green]Ledger is VALID[/bold green] ({result['checked_events']} events checked)"
        )
        stats = result.get("enrichment_stats", {})
        console.print(
            f"Enrichment: [green]Indexed: {stats.get('indexed', 0)}[/green] | "
            f"[yellow]Pending: {stats.get('pending', 0)}[/yellow] | "
            f"[red]Failed: {stats.get('failed', 0)}[/red]"
        )

        with store.tx() as conn:
            checkpoints = conn.execute(
                "SELECT checkpoint_id, root_hash, start_event_id, end_event_id, event_count "
                "FROM ledger_checkpoints ORDER BY checkpoint_id ASC"
            ).fetchall()

        if checkpoints:
            console.print("\nMerkle Checkpoints:")
            for cp in checkpoints:
                cp_id = cp["checkpoint_id"]
                start_ev = cp["start_event_id"]
                end_ev = cp["end_event_id"]
                root_hash = cp["root_hash"]
                console.print(f"  Checkpoint #{cp_id} (root: {root_hash})")

                with store.tx() as conn:
                    start_row = conn.execute(
                        "SELECT rowid FROM ledger_events WHERE event_id = ?", (start_ev,)
                    ).fetchone()
                    end_row = conn.execute(
                        "SELECT rowid FROM ledger_events WHERE event_id = ?", (end_ev,)
                    ).fetchone()

                if start_row and end_row:
                    start_rowid = start_row[0]
                    end_rowid = end_row[0]
                    with store.tx() as conn:
                        event_rows = conn.execute(
                            "SELECT hash FROM ledger_events WHERE rowid >= ? AND rowid <= ? ORDER BY rowid ASC",
                            (start_rowid, end_rowid),
                        ).fetchall()

                    hashes = [r["hash"] for r in event_rows if r["hash"]]
                    if hashes:
                        from legacy_research.consensus.merkle import MerkleTree

                        tree = MerkleTree(hashes)
                        for lvl_idx, level in enumerate(tree.tree):
                            if lvl_idx == 0:
                                for leaf_idx, leaf_hash in enumerate(level):
                                    console.print(f"    Leaf {leaf_idx}: {leaf_hash}")
                            else:
                                console.print(f"    Node L{lvl_idx}:")
                                for _node_idx, node_hash in enumerate(level):
                                    console.print(f"      Node L{lvl_idx}: {node_hash}")
    else:
        violations = result["violations"]
        console.print(f"[bold red]Ledger is COMPROMISED[/bold red]: {len(violations)} violations")
        for v in violations[:10]:
            console.print(f"  - {v}")


@ledger_cmds.command("checkpoint")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--batch", default=10, help="Events per checkpoint")
def create_checkpoint(db: str, batch: int):
    """Compute and store a Merkle root for uncheckpointed events."""
    store = LedgerStore(db)
    verifier = LedgerVerifier(store)

    with console.status("[bold cyan]Creating Merkle checkpoint..."):
        root_id = verifier.create_checkpoint(batch_size=batch)

    if root_id:
        console.print(f"[bold green]Checkpoint created successfully.[/bold green] ID: {root_id}")
    else:
        console.print(
            "[yellow]No new events available for checkpointing (batch size not reached).[/yellow]"
        )


@ledger_cmds.command("export")
@click.argument("export_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--tenant-id", required=True, help="Tenant ID for the export")
@click.option("--stream-id", required=True, help="Stream ID for the export")
@click.option("--include-verification-report", is_flag=True, help="Include verification report")
def export_ledger_cmd(
    export_dir: Path,
    db: str,
    tenant_id: str,
    stream_id: str,
    include_verification_report: bool,
):
    """Export forensic ledger package in public-v1-strict format."""
    from legacy_research.ledger.public_export import (
        _b64url_encode,
    )

    store = LedgerStore(db)
    with store.tx() as conn:
        rows = conn.execute(
            "SELECT payload_json, prev_hash, hash FROM ledger_events ORDER BY rowid ASC"
        ).fetchall()

    if not rows:
        raise click.ClickException("No events found in database to export")

    events = [json.loads(r["payload_json"]) for r in rows]

    actor_permissions = {}
    for ev_data in events:
        actor_id = ev_data.get("actor") or "ghost-actor"
        action = ev_data.get("action") or "unknown"
        if actor_id not in actor_permissions:
            actor_permissions[actor_id] = set()
        actor_permissions[actor_id].add(action)

    actor_keys = {}
    pk_records = []
    for actor_id, perms in actor_permissions.items():
        priv_key = Ed25519PrivateKey.generate()
        actor_keys[actor_id] = priv_key
        key_id = f"ed25519:{actor_id}:key-1"
        pk_records.append(
            public_key_record(
                key_id=key_id,
                actor_id=actor_id,
                public_key=priv_key.public_key(),
                permissions=list(perms),
            )
        )

    public_events = []
    prev_hash = "GENESIS"
    for i, ev_data in enumerate(events):
        actor_id = ev_data.get("actor") or "ghost-actor"
        priv_key = actor_keys[actor_id]
        key_id = f"ed25519:{actor_id}:key-1"

        target_val = ev_data.get("target")
        detail_val = {
            "tool": ev_data.get("tool"),
            "action": ev_data.get("action"),
            "result": ev_data.get("result"),
            "intent": ev_data.get("intent"),
            "metadata": ev_data.get("metadata"),
        }
        detail_val = {
            k: v
            for k, v in detail_val.items()
            if k not in ("content", "payload", "plaintext", "fact_content")
        }

        event_dict = {
            "schema_version": "cortex-ledger-event-v1",
            "stream_id": stream_id,
            "tenant_id": tenant_id,
            "sequence": i + 1,
            "event_id": ev_data.get("event_id"),
            "nonce": f"nonce_{ev_data.get('event_id')}",
            "issued_at": ev_data.get("timestamp") or ev_data.get("ts"),
            "recorded_at": ev_data.get("timestamp") or ev_data.get("ts"),
            "actor_id": actor_id,
            "actor_key_id": key_id,
            "action": ev_data.get("action"),
            "project": (ev_data.get("metadata") or {}).get("project") or actor_id,
            "target": target_val,
            "detail": detail_val,
            "prev_hash": prev_hash,
            "hash_alg": "sha256",
            "signature_alg": "ed25519",
        }

        # Compute hash without hash and origin_signature fields
        event_hash = _event_hash(event_dict)
        event_dict["hash"] = event_hash

        # Compute signature over event dict which now contains hash
        canonical_bytes = _event_signature_scope(event_dict)
        sig_bytes = priv_key.sign(canonical_bytes)
        event_dict["origin_signature"] = _b64url_encode(sig_bytes)

        public_events.append(event_dict)
        prev_hash = event_hash

    export_private_key = Ed25519PrivateKey.generate()
    export_authority = ExportAuthority(
        key_id="ed25519:export-authority:ghost-export-001",
        actor_id="export-authority-ghost",
        private_key=export_private_key,
        environment="test",
    )

    result = write_public_ledger_export(
        events=public_events,
        export_dir=export_dir,
        public_keys=pk_records,
        export_authority=export_authority,
        export_id="export-ghost-test-001",
        tenant_id=tenant_id,
        stream_id=stream_id,
        include_verification_report=include_verification_report,
        allow_overwrite=True,
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


ledger_cmds_click = ledger_cmds
cli.add_command(ledger_cmds, name="trust-ledger")
