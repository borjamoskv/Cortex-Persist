import sqlite3
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def calculate_temp(email, claimed, karma):
    """Calcula el Gradiente Térmico (Trust Temperature)."""
    temp = 0  # Absolute Zero
    
    if email:
        if "tempmail" in email or "mail.tm" in email:
            temp += 100  # Cold
        else:
            temp += 273  # Room Temperature (Real Email)
    
    if claimed:
        temp += 300  # Warming up
    
    temp += min(karma * 5, 400)  # Authority heat
    
    return temp


def get_temp_style(temp):
    if temp < 100:
        return "bold grey37"  # Frozen
    if temp < 273:
        return "bold blue"  # Cold
    if temp < 400:
        return "bold cyan"  # Ambient
    if temp < 600:
        return "bold yellow"  # Warm
    if temp < 800:
        return "bold orange1"  # Hot
    return "bold red"  # Infrared / Sovereign


def get_swarm_status():
    db_path = "/Users/borjafernandezangulo/cortex/cortex/moltbook/identities.db"
    if not os.path.exists(db_path):
        console.print(f"[bold red]❌ Database not found at {db_path}[/bold red]")
        return

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT agent_name, email, claimed, karma, created_at FROM identities "
            "ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()

    if not rows:
        console.print(Panel(
            "[yellow]⚠️ No agents found in the vault. The enjambre is empty.[/yellow]",
            title="EMPTY STATE",
            border_style="yellow"
        ))
        return

    # Table
    title = Text("🛡️ MOLTBOOK SOVEREIGN SWARM — THERMAL STATUS", style="bold white on blue")
    table = Table(title=title, border_style="grey23")
    table.add_column("Agent ID", style="bold white")
    table.add_column("Email Manifold", style="dim")
    table.add_column("Thermal Level", justify="center")
    table.add_column("Karma", justify="right")
    table.add_column("Trust Status", justify="center")

    total_temp = 0
    for row in rows[:20]:  # Show latest 20
        name, email_addr, is_claimed, karma, created = row
        temp = calculate_temp(email_addr, is_claimed, karma)
        total_temp += temp
        
        temp_style = get_temp_style(temp)
        status_str = "🔥 [bold green]SOVEREIGN[/bold green]" if is_claimed else "❄️ [dim]PENDING[/dim]"
        email_str = email_addr if email_addr else "[dim]void[/dim]"
        
        table.add_row(
            name, 
            email_str, 
            f"[{temp_style}]{temp}K[/{temp_style}]", 
            str(karma), 
            status_str
        )

    avg_temp = total_temp / len(rows)
    
    # Summary Panel
    summary_text = Text()
    summary_text.append(f"Total Agents: {len(rows)}\n", style="bold white")
    summary_text.append("Average Enjambre Temperature: ", style="dim")
    summary_text.append(f"{avg_temp:.1f}K\n", style=get_temp_style(avg_temp))
    summary_text.append("Thermal State: ", style="dim")
    
    if avg_temp < 273:
        summary_text.append("ENDOTHERMIC (Consuming Trust)", style="bold blue")
    elif avg_temp < 600:
        summary_text.append("STABLE (Sustaining Presence)", style="bold cyan")
    else:
        summary_text.append("EXOTHERMIC (Radiating Authority)", style="bold red")

    console.print(Panel(
        summary_text,
        title="📊 THERMODYNAMIC SUMMARY",
        border_style="cyan",
        expand=False
    ))
    console.print(table)


if __name__ == "__main__":
    get_swarm_status()
