import click
import asyncio
from rich.console import Console

from cortex.cli.common import cli, run_async
from cortex.engine.auth_gateway import AuthGateway
from cortex.engine import CortexEngine

console = Console()

@cli.group()
def auth() -> None:
    """Manage Operator Override requests for Sovereign Daemon."""
    pass

@auth.command("approve")
@click.argument("req_id")
@run_async
async def approve_request(req_id: str) -> None:
    """Approves a pending authorization request with Ed25519 cryptographic signature."""
    from cortex.extensions.security.signatures import get_default_signer
    
    engine = CortexEngine()
    auth_gw = AuthGateway(engine)
    
    # 1. Fetch payload to sign
    try:
        conn = engine.pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT state_payload FROM auth_requests WHERE id = ? AND status = 'PENDING'", (req_id,))
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
        console.print("[bold red]✗ No valid Ed25519 private key found in keyring. Cannot sign override.[/bold red]")
        return
        
    try:
        # We sign the payload treating req_id as fact_hash
        signature = signer.sign(content=state_payload, fact_hash=req_id)
        pub_key = signer.public_key_b64
        console.print(f"[cyan]Signature generated using Ed25519: {signature[:16]}...[/cyan]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to generate cryptographic signature: {e}[/bold red]")
        return
    
    # 3. Submit
    success = await auth_gw.approve_request(req_id, signature_b64=signature, public_key_b64=pub_key)
    if success:
        console.print(f"[bold green]✓ Request {req_id} APPROVED (ZK-Sealed).[/bold green]")
        console.print("Sovereignty Runtime will now proceed with mitigation.")
    else:
        console.print(f"[bold red]✗ Failed to approve request {req_id}.[/bold red]")
        
@auth.command("reject")
@click.argument("req_id")
@run_async
async def reject_request(req_id: str) -> None:
    """Rejects a pending authorization request."""
    engine = CortexEngine()
    auth_gw = AuthGateway(engine)
    
    success = await auth_gw.reject_request(req_id)
    if success:
        console.print(f"[bold yellow]✓ Request {req_id} REJECTED.[/bold yellow]")
        console.print("Mitigation has been aborted.")
    else:
        console.print(f"[bold red]✗ Failed to reject request {req_id}.[/bold red]")
        
@auth.command("list")
@run_async
async def list_requests() -> None:
    """Lists pending authorization requests."""
    engine = CortexEngine()
    try:
        conn = engine.pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, status, hypothesis FROM auth_requests WHERE status = 'PENDING'")
        rows = cursor.fetchall()
        
        if not rows:
            console.print("[green]No pending authorization requests.[/green]")
            return
            
        for row in rows:
            console.print(f"[bold cyan]{row[0]}[/bold cyan] | [yellow]{row[1]}[/yellow] | {row[2]}")
    except Exception as e:
        console.print(f"[bold red]Failed to fetch requests: {e}[/bold red]")
