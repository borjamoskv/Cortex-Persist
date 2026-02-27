#!/usr/bin/env python3
"""
CORTEX PRE-COMMIT HOOK: ENTROPY-0
Zero-Debt & Zero-Trust Enforcement Protocol (v6.0 Sovereign Standard)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
MAX_FILES_PER_COMMIT = 15

# Veto Patterns: Any line matching these will block the commit.
BLOCKED_PATTERNS = {
    "SECRET_API_KEY": re.compile(r"(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16})", re.IGNORECASE),
    "TODO_OR_FIXME": re.compile(r"\b(TODO|FIXME|HACK|XXX)\b:?"),
    "DEBUG_PRINT": re.compile(r"^\s*(print\(|console\.log\()", re.IGNORECASE),
}

# File extensions where TODO/FIXME checks are skipped (prose, not code).
PROSE_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}

# Paths where print() is legitimate (CLI output, tests, scripts, diagnostics).
PRINT_ALLOWED_PREFIXES = (
    "cortex/cli/", "tests/", "scripts/", "examples/",
    "cortex/database/", "cortex/hooks/", "cortex/launchpad/",
)

# Operational Dirt: File names/paths that should never be tracked directly.
BLOCKED_PATHS = {
    ".DS_Store",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def get_staged_files() -> list[str]:
    """Retrieves a list of files currently staged for commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        console.print("[bold red]ERROR: Falta contexto de git o comando fallido.[/bold red]")
        sys.exit(1)
    
    files = result.stdout.strip().split("\n")
    return [f for f in files if f.strip() and os.path.isfile(f)]

def get_staged_file_content(filepath: str) -> str:
    """Retrieves the staged content of a given file."""
    result = subprocess.run(
        ["git", "show", f":{filepath}"],
        capture_output=True,
        text=True
    )
    return result.stdout

def print_violation_panel(title: str, message: str, color: str = "red") -> None:
    """Prints a styled violation panel."""
    console.print(Panel(
        f"[bold {color}]{message}[/bold {color}]",
        title=f"🚨 CORTEX VIOLATION: {title} 🚨",
        border_style=color
    ))

# ---------------------------------------------------------
# METRICS & VALIDATION
# ---------------------------------------------------------
def main():
    staged_files = get_staged_files()
    
    if not staged_files:
        sys.exit(0) # Nothing to check
    
    # 1. Monolithic Commit Check (Frankensteins)
    if len(staged_files) > MAX_FILES_PER_COMMIT:
        print_violation_panel(
            "COMMITS MONOLÍTICOS (FRANKENSTEIN)",
            f"Intentas realizar commit de {len(staged_files)} archivos a la vez.\n\n"
            f"El Límite Soberano es {MAX_FILES_PER_COMMIT}. \n"
            "Separa conceptualmente la tarea en commits atómicos.",
            color="yellow"
        )
        sys.exit(1)

    errors_found = False

    for file in staged_files:
        # Self-exclusion: don't scan the hook's own source
        if file == "scripts/zero_debt.py":
            continue
        # 2. Operational Dirt Check (Ignoring .gitignore rules by brute-force addition)
        if any(dirt in file for dirt in BLOCKED_PATHS):
            print_violation_panel(
                "PUREZA OPERATIVA VULNERADA",
                f"El archivo/ruta '{file}' es Basura Operativa.\n\n"
                "Usa un .gitignore correctamente. No subas cachés ni dependencias.",
                color="red"
            )
            errors_found = True
            continue

        # Skip binary files or non-text files to avoid decode errors
        if file.endswith(('.mp4', '.sqlite', '.png', '.jpg', '.jpeg', '.pdf', '.db')):
            continue
            
        content = get_staged_file_content(file)
        lines = content.splitlines()
        
        is_prose = Path(file).suffix.lower() in PROSE_EXTENSIONS

        for i, line in enumerate(lines, 1):
            # 3. Secret & Entropy Inspections
            for rule_name, pattern in BLOCKED_PATTERNS.items():
                # Skip TODO/FIXME/DEBUG checks in prose files (markdown, etc.)
                if is_prose and rule_name in ("TODO_OR_FIXME", "DEBUG_PRINT"):
                    continue
                # Skip DEBUG_PRINT in CLI, tests, scripts (print is legitimate there)
                if rule_name == "DEBUG_PRINT" and any(file.startswith(p) for p in PRINT_ALLOWED_PREFIXES):
                    continue
                if pattern.search(line):
                    print_violation_panel(
                        f"REGLA QUEBRANTADA: {rule_name}",
                        f"Archivo: {file} (Línea {i})\nContenido conflictivo:\n> {line.strip()}",
                        color="red"
                    )
                    errors_found = True

    if errors_found:
        console.print("\n[bold red][✗] El commit ha sido ABORTADO por el protocolo ENTROPY-0.[/bold red]")
        console.print("[bold yellow]Limpieza requerida para mantener Densidad Infinita (130/100).[/bold yellow]\n")
        sys.exit(1)

    # Allow commit
    sys.exit(0)

if __name__ == "__main__":
    main()
