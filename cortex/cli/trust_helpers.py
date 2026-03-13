"""Helper functions for Trust and Compliance CLI commands."""

import json
import sqlite3

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def _find_transaction(conn, fact_id: int, fact_tx_id: int | None):
    """Look up the transaction for a fact, trying direct ID then join."""
    tx = None
    if fact_tx_id:
        tx = conn.execute(
            "SELECT id, hash, prev_hash, action, timestamp FROM transactions WHERE id = ?",
            (fact_tx_id,),
        ).fetchone()
    if not tx:
        tx = conn.execute(
            "SELECT t.id, t.hash, t.prev_hash, t.action, t.timestamp "
            "FROM facts f JOIN transactions t ON f.tx_id = t.id "
            "WHERE f.id = ?",
            (fact_id,),
        ).fetchone()
    return tx


def _verify_chain(conn, tx_id: int, prev_hash: str | None) -> tuple[bool, str]:
    if not prev_hash:
        return True, "[green]OK[/green]"

    prev_tx = conn.execute(
        "SELECT hash FROM transactions WHERE id = ?",
        (tx_id - 1,),
    ).fetchone()

    if prev_tx and prev_tx[0] != prev_hash:
        return False, "[red]BROKEN - prev_hash mismatch[/red]"
    return True, "[green]OK[/green]"


def _check_merkle(conn, tx_id: int):
    try:
        return conn.execute(
            "SELECT id, root_hash, tx_start_id, tx_end_id, created_at "
            "FROM merkle_roots "
            "WHERE tx_start_id <= ? AND tx_end_id >= ? LIMIT 1",
            (tx_id, tx_id),
        ).fetchone()
    except (sqlite3.Error, OSError, RuntimeError):
        return None

def _render_verification_certificate(
    fact: tuple, tx: tuple, chain_valid: bool, chain_msg: str, checkpoint: tuple | None
) -> None:
    fid, proj, content, ftype, created, _fact_tx_id = fact
    _, tx_hash, prev_hash, _action, _tx_time = tx

    table = Table(title="CORTEX Verification Certificate", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Fact ID", f"#{fid}")
    table.add_row("Project", proj)
    table.add_row("Type", ftype)
    table.add_row("Created", created)
    table.add_row("Content", content[:200])
    table.add_row("", "")
    table.add_row("TX Hash", tx_hash[:32] + "...")
    table.add_row("Prev Hash", (prev_hash or "genesis")[:32] + "...")
    table.add_row("Chain Link", chain_msg)

    if checkpoint:
        cp_id, merkle_root, start, end, cp_time = checkpoint
        table.add_row("", "")
        table.add_row("Merkle Root", merkle_root[:32] + "...")
        table.add_row("Checkpoint", f"#{cp_id} (TX #{start} to #{end})")
        table.add_row("Sealed", cp_time)
        table.add_row("Merkle Status", "[green]Included in sealed checkpoint[/green]")
    else:
        table.add_row("Merkle", "[yellow]Not yet checkpointed[/yellow]")

    overall = "[green]VERIFIED[/green]" if chain_valid else "[red]INTEGRITY VIOLATION[/red]"
    console.print(table)
    console.print(Panel(overall, title="Verdict"))


def _safe_count(conn, query: str) -> int:
    """Execute a COUNT query, return 0 on error."""
    try:
        return conn.execute(query).fetchone()[0]
    except (sqlite3.Error, OSError, RuntimeError):
        return 0


def _extract_agents(conn) -> set[str]:
    """Parse agent tags from facts."""
    rows = conn.execute(
        "SELECT DISTINCT tags FROM facts WHERE tags LIKE '%agent:%' AND valid_until IS NULL"
    ).fetchall()
    agents: set[str] = set()
    for row in rows:
        if not row[0]:
            continue
        try:
            tags = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            tags = [t.strip() for t in row[0].split(",")]
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("agent:"):
                agents.add(tag)
    return agents


def _check_chain_integrity(conn) -> tuple[bool, int]:
    """Verify transaction hash chain. Returns (valid, violations)."""
    try:
        txs = conn.execute(
            "SELECT id, hash, prev_hash FROM transactions ORDER BY id LIMIT 1000"
        ).fetchall()
    except (sqlite3.Error, OSError, RuntimeError):
        return True, 0
    violations = sum(1 for i in range(1, len(txs)) if txs[i][2] and txs[i][2] != txs[i - 1][1])
    return violations == 0, violations

def _get_audit_trail(conn, project: str, limit: int):
    """Internal helper to get the audit trail rows."""
    from cortex.cli.errors import err_empty_results

    conditions = ["f.valid_until IS NULL"]
    params: list = []

    if project:
        conditions.append("f.project = ?")
        params.append(project)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT f.id, f.project, f.content, f.fact_type,
               f.created_at, t.hash
        FROM facts f
        LEFT JOIN transactions t ON f.tx_id = t.id
        WHERE {where_clause}
        ORDER BY f.id DESC
        LIMIT ?
    """
    rows = conn.execute(query, params).fetchall()

    if not rows:
        err_empty_results("audit entries")
        return None

    table = Table(title=f"CORTEX Audit Trail ({len(rows)} entries)")
    table.add_column("ID", style="dim")
    table.add_column("Time")
    table.add_column("Project", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Content")
    table.add_column("Hash", style="dim")

    for row in rows:
        fid, proj, content, ftype, created, tx_hash = row
        table.add_row(
            str(fid),
            created[:19] if created else "-",
            proj,
            ftype,
            content[:80] + ("..." if len(content) > 80 else ""),
            (tx_hash or "-")[:12] + "..." if tx_hash else "-",
        )
    return table
