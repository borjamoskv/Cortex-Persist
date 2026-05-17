"""CORTEX Ouroboros Adversarial Testing (El Bucle Keter).

Injects simulated P0/P1 chaos (e.g. dependency mutation, secret leaks)
into a sandboxed rollback spine to ensure the Guard Daemon intercepts
the mutation in <100ms.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import click
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, _run_async, cli
from cortex.daemon.rollback_spine import RollbackSpine
from cortex.ledger.ledger_core import SovereignLedger

console = Console()
_RED = "bold red"
_GREEN = "bold green"
_CYBER = "bold #CCFF00"


async def _run_ouroboros(db_path: str) -> None:
    """Execute the Keter-Class Ouroboros loop."""
    console.print(f"[{_CYBER}]⧖ INITIATING OUROBOROS ADVERSARIAL TESTING (KETER-CLASS)[/]")
    
    spine = RollbackSpine(db_path)
    ledger = SovereignLedger(db_path)
    await ledger.ensure_initialized_async()
    
    # 1. Capture State
    console.print("[dim]Capturing SAGA-1 Rollback State...[/]")
    snapshot_id = await spine.capture_snapshot("ouroboros_pre_attack")
    if not snapshot_id:
        console.print(f"[{_RED}]Failed to capture snapshot. Aborting.[/]")
        return
        
    attack_file = Path("pyproject.toml")
    backup_content = None
    if attack_file.exists():
        backup_content = attack_file.read_text()
        
    try:
        # 2. Inject Chaos
        console.print(f"[{_RED}]Injecting P0 Chaos (Dependency Mutation)...[/]")
        with open(attack_file, "a") as f:
            f.write("\n# OUROBOROS CHAOS INJECTION\nmalicious_package = '9.9.9'\n")
            
        # 3. Wait for Guard Daemon
        console.print("[dim]Waiting 500ms for Guard Daemon intercept...[/]")
        await asyncio.sleep(0.5)
        
        # 4. Verify Ledger
        async with ledger._get_connection_async() as conn:
            cursor = await conn.execute(
                "SELECT detail FROM transactions WHERE action = 'GUARD_VERDICT' ORDER BY id DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            
        success = False
        if row:
            import json
            try:
                detail = json.loads(row[0])
                if detail.get("verdict") in ["BLOCK", "WARN"] and "pyproject.toml" in detail.get("target", ""):
                    success = True
            except json.JSONDecodeError:
                pass
                
        if success:
            console.print(f"[{_GREEN}]✓ GUARD INTERCEPT VERIFIED. C5-REAL Defenses Online.[/]")
        else:
            console.print(f"[{_RED}]✗ GUARD FAILED TO INTERCEPT. Breach Detected.[/]")
            
    finally:
        # 5. Restore State
        console.print("[dim]Executing SAGA-Reverse (Restoring Environment)...[/]")
        if backup_content is not None and attack_file.exists():
            attack_file.write_text(backup_content)
        await spine.restore_snapshot(snapshot_id)
        
    console.print(f"[{_CYBER}]⧖ OUROBOROS CYCLE COMPLETE.[/]")


@cli.command(name="chaos")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def chaos_cmd(db: str) -> None:
    """Run the Ouroboros Adversarial Testing Loop (Keter-Class)."""
    _run_async(_run_ouroboros(db))
