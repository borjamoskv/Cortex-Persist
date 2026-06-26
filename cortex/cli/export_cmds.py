# [C5-REAL] Exergy-Maximized
"""
EU AI Act Compliance Bundle Exporter.
"""

import json
import logging
import zipfile
from pathlib import Path

import aiosqlite
import click
from rich.console import Console

from cortex.cli.main import cli

console = Console()
logger = logging.getLogger("cortex.cli.export")


@cli.group()
def compliance() -> None:
    """Enterprise Compliance & Audit tools (EU AI Act, SOC2)."""
    pass


@compliance.command("export-bundle")
@click.option("--tenant-id", required=True, help="Tenant ID to export compliance data for.")
@click.option("--output", default="audit_bundle.zip", help="Output ZIP file path.")
def export_bundle(tenant_id: str, output: str) -> None:
    """Exports a cryptographic compliance bundle for third-party auditing."""
    import asyncio

    async def _export():
        db_path = "cortex.db"
        output_path = Path(output)

        console.print(
            f"[bold blue]Initiating EU AI Act Compliance Export for tenant:[/bold blue] {tenant_id}"
        )

        bundle_dir = Path(".cortex_bundle_tmp")
        bundle_dir.mkdir(exist_ok=True)

        # 1. Export Audit Ledger for the tenant
        ledger_path = bundle_dir / "audit_ledger.json"
        from cortex.database.core import connect_async
        async with await connect_async(db_path) as conn:
            # We assume security_audit_log exists
            try:
                cursor = await conn.execute(
                    "SELECT audit_id, timestamp, actor_id, action, status, prev_hash, signature, external_anchor FROM security_audit_log WHERE tenant_id = ? ORDER BY rowid ASC",
                    (tenant_id,),
                )
                rows = await cursor.fetchall()

                ledger_data = []
                for row in rows:
                    anchor = json.loads(row[7]) if row[7] else None
                    ledger_data.append(
                        {
                            "audit_id": row[0],
                            "timestamp": row[1],
                            "actor_id": row[2],
                            "action": row[3],
                            "status": row[4],
                            "prev_hash": row[5],
                            "signature": row[6],
                            "external_anchor": anchor,
                        }
                    )

                with open(ledger_path, "w") as f:
                    json.dump(ledger_data, f, indent=2)

                console.print(
                    f"  [green]✓[/green] Exported {len(ledger_data)} cryptographically linked ledger entries."
                )
            except Exception as e:
                console.print(f"  [red]✗[/red] Ledger export failed: {e}")

        # 2. Package Public Keys for signature verification
        # (Assuming the public key can be pulled from the local environment)
        pk_path = bundle_dir / "audit_sovereign_pub.pem"
        try:
            from cryptography.hazmat.primitives import serialization

            from cortex.audit.ledger import EnterpriseAuditLedger

            # Get public key from a temporary instance
            from cortex.database.core import connect_async
            async with await connect_async(db_path) as c:
                ledger = EnterpriseAuditLedger(c)
                pub_pem = ledger.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                with open(pk_path, "wb") as f:
                    f.write(pub_pem)
                console.print("  [green]✓[/green] Exported Sovereign Audit Public Key.")
        except Exception as e:
            console.print(f"  [red]✗[/red] Public Key export failed: {e}")

        # 3. Create ZIP bundle
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if ledger_path.exists():
                zf.write(ledger_path, ledger_path.name)
            if pk_path.exists():
                zf.write(pk_path, pk_path.name)

        # Cleanup
        if ledger_path.exists():
            ledger_path.unlink()
        if pk_path.exists():
            pk_path.unlink()
        if bundle_dir.exists():
            bundle_dir.rmdir()

        console.print(
            f"[bold green]Compliance Bundle successfully exported to:[/bold green] {output_path.absolute()}"
        )
        console.print("\n[dim]To verify this bundle, an external auditor can run:[/dim]")
        console.print(f"  [bold]cortex compliance verify-bundle {output_path.name}[/bold]")

    asyncio.run(_export())
