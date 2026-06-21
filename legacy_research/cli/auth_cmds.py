# [C5-REAL] Exergy-Maximized

import click
from rich.console import Console

from cortex.cli.common import cli, run_async
from cortex.engine import CortexEngine
from cortex.engine.auth_gateway import QuorumGateway

console = Console()


@cli.group()
def auth() -> None:
    """Manage BFT Consensus Quorum requests."""


@auth.command("vote")
@click.argument("req_id")
@run_async
async def submit_vote(req_id: str) -> None:
    """Submits a cryptographic vote for a pending consensus request."""
    from cortex.extensions.security.signatures import get_default_signer

    engine = CortexEngine()
    auth_gw = QuorumGateway(engine)

    # 1. Fetch payload to sign
    try:
        conn = engine.pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT state_payload FROM quorum_requests WHERE id = ? AND status = 'PENDING'",
            (req_id,),
        )
        row = cursor.fetchone()
        if not row:
            console.print(f"[bold red]✗ Request {req_id} not found or not PENDING.[/bold red]")
            return
        state_payload = row[0]
    except Exception as e:
        console.print(f"[bold red]✗ Failed to read request: {e}[/bold red]")
        return

    # 2. Cryptographic signature
    signer = get_default_signer()
    if not signer or not signer.can_sign:
        console.print(
            "[bold red]✗ No valid Ed25519 private key found in keyring. Cannot sign override.[/bold red]"
        )
        return

    try:
        signature = signer.sign(content=state_payload, fact_hash=req_id)
        pub_key = signer.public_key_b64
        console.print(f"[cyan]Signature generated using Ed25519: {signature[:16]}...[/cyan]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to generate cryptographic signature: {e}[/bold red]")
        return

    # 3. Submit Vote
    # For CLI purposes, the operator implies semantic_truth = True by explicitly voting
    success = await auth_gw.submit_vote(
        req_id, signature_b64=signature, public_key_b64=pub_key, semantic_truth=True
    )
    if success:
        console.print(f"[bold green]✓ Vote registered for {req_id}.[/bold green]")
    else:
        console.print(f"[bold red]✗ Failed to register vote for {req_id}.[/bold red]")


@auth.command("reject")
@click.argument("req_id")
@run_async
async def reject_request(req_id: str) -> None:
    """Rejects a pending request directly (admin override)."""
    engine = CortexEngine()
    auth_gw = QuorumGateway(engine)

    success = await auth_gw.reject_request(req_id)
    if success:
        console.print(f"[bold yellow]✓ Request {req_id} REJECTED.[/bold yellow]")
    else:
        console.print(f"[bold red]✗ Failed to reject request {req_id}.[/bold red]")


@auth.command("list")
@run_async
async def list_requests() -> None:
    """Lists pending BFT quorum requests."""
    engine = CortexEngine()
    try:
        conn = engine.pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status, hypothesis, signatures_json FROM quorum_requests WHERE status = 'PENDING'"
        )
        rows = cursor.fetchall()

        if not rows:
            console.print("[green]No pending consensus requests.[/green]")
            return

        import json

        for row in rows:
            sigs = json.loads(row[3])
            console.print(
                f"[bold cyan]{row[0]}[/bold cyan] | [yellow]{row[1]}[/yellow] | Votes: {len(sigs)} | {row[2]}"
            )
    except Exception as e:
        console.print(f"[bold red]Failed to fetch requests: {e}[/bold red]")
