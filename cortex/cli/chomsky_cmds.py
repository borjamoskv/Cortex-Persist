import os

import click

from cortex.cli.common import console


@click.group(name="chomsky", help="CHOMSKY-Ω Syntactic Compressor (0% Fact Drop).")
def chomsky_group() -> None:
    pass

@chomsky_group.command(name="compress")
@click.argument("text", type=str)
def compress_cmd(text: str) -> None:
    """Returns the syntactically pruned text."""
    try:
        from cortex.extensions.skills.chomsky.engine import compress
    except ImportError:
        console.print("[red]CHOMSKY Engine not found. Ensure it is consolidated in cortex/extensions/skills/chomsky/engine.py[/]")
        return

    res = compress(text)
    console.print("[bold cyan]CHOMSKY-Ω RESULT[/]")
    console.print(f"Original: {text}")
    console.print(f"Compressed: [green]{res['compressed_payload']}[/]")
    console.print(f"Tokens Saved: {res['tokens_saved']} | Mode: {res['ast_mode']}")


@chomsky_group.command(name="parse")
@click.argument("text", type=str)
def parse_cmd(text: str) -> None:
    """Outputs the parsed AST tree, highlighting the exergy nodes versus thermal noise."""
    try:
        from cortex.extensions.skills.chomsky.engine import compress
    except ImportError:
        console.print("[red]CHOMSKY Engine not found.[/]")
        return
        
    res = compress(text)
    console.print(f"\n[bold magenta]AST PARSE (Mode: {res['ast_mode']})[/]")
    console.print(f"Proper Nouns Retained: {res['proper_nouns_retained']}")
    console.print(f"Numbers Retained: {res['numbers_retained']}")
    console.print(f"Exergy (Retained): [green]{res['compressed_payload']}[/]")


@chomsky_group.command(name="audit")
def audit_cmd() -> None:
    """Runs mechanical Sortu verification."""
    import subprocess
    
    verify_script = os.path.expanduser("~/.gemini/antigravity/skills/chomsky-omega/verify_chomsky.py")
    if not os.path.exists(verify_script):
        console.print(f"[red]Verification script not found at {verify_script}[/]")
        return
        
    result = subprocess.run(["python3", verify_script], capture_output=True, text=True)
    if result.returncode == 0:
        console.print("[bold green]CHOMSKY-Ω VERIFICATION PASS[/]")
        console.print(result.stdout)
    else:
        console.print("[bold red]CHOMSKY-Ω VERIFICATION FAIL[/]")
        console.print(result.stdout)
        console.print(result.stderr)
