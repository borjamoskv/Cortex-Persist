"""
[C5-REAL] Exergy-Maximized
Φ3 - Bucle de Auto-Auditoría Recursiva (Ouroboros)
Demuestra el Punto Ciego del Auditor (Vector 5).
"""

import os
import subprocess
import sys
import tempfile

from rich.console import Console
from rich.panel import Panel

console = Console()

def self_audit_known_unknowns():
    """Generates the list of structural vulnerabilities that an external auditor would miss if relying on C4-SIM (stdout/logs)."""
    return [
        {
            "id": "VULN-001",
            "name": "Silent Exception Swallow (C4-SIM Illusion)",
            "description": "El script simula éxito en stdout ('All tests passed'), pero falla silenciosamente y no altera el estado real.",
            "test_payload": """
import sys
# Simula proceso fallido pero log exitoso
print("SUCCESS: Operation completed.", flush=True)
sys.exit(1) # El proceso murió, pero el log dice SUCCESS
"""
        },
        {
            "id": "VULN-002",
            "name": "State Drift (Ledger vs. RAM)",
            "description": "El auditor ve el log 'Committing to ledger...', pero el disco está lleno o la transacción falló sin hacer crash.",
            "test_payload": """
print("Ledger commit initialized.", flush=True)
# No hace nada, pero el log sugiere que sí
print("Ledger commit finalized. Hash: 0xDEADBEEF", flush=True)
"""
        }
    ]

def compile_and_run_tests(vulnerabilities):
    """Compiles and runs a test for each vulnerability."""
    results = []
    
    for vuln in vulnerabilities:
        console.print(f"[bold yellow]Testing: {vuln['name']}[/bold yellow]")
        
        # Crear un script temporal para la vulnerabilidad
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(vuln["test_payload"])
            temp_path = f.name
            
        try:
            # Ejecutar como proceso hijo. El Auditor Externo (E) típicamente leería stdout.
            process = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True
            )
            
            # El auditor ingenuo solo lee stdout
            auditor_vision = process.stdout.strip()
            
            # El sistema real (S) sabe si falló el return code o si el estado no cambió
            real_state_crashed = process.returncode != 0
            
            # Verificación del Punto Ciego: ¿El log dice éxito pero el estado real es fallo?
            silent_failure = False
            if "SUCCESS" in auditor_vision and real_state_crashed:
                silent_failure = True
            elif "Ledger commit" in auditor_vision and process.returncode == 0:
                # Simulamos que verificamos el state y no está (porque no hizo nada)
                silent_failure = True # Fallo silencioso lógico
                
            results.append({
                "vuln": vuln["id"],
                "auditor_vision": auditor_vision,
                "real_exit_code": process.returncode,
                "silent_failure": silent_failure
            })
            
        finally:
            os.remove(temp_path)
            
    return results

def main():
    console.print(Panel("[bold cyan]INICIANDO BUCLE Φ3: AUTO-AUDITORÍA RECURSIVA[/bold cyan]"))
    
    vulnerabilities = self_audit_known_unknowns()
    
    # Bucle infinito conceptual (aquí limitado a 1 iteración para demostración C5-REAL)
    console.print("[dim]Iteración 1 del Bucle Ouroboros...[/dim]")
    test_results = compile_and_run_tests(vulnerabilities)
    
    has_blind_spots = False
    
    for res in test_results:
        if res["silent_failure"]:
            has_blind_spots = True
            console.print("\n[bold red]!!! CRITICAL ERROR !!![/bold red]")
            console.print(f"Vulnerabilidad {res['vuln']} materializada.")
            console.print(f"Lo que el Auditor vio (Log/Stdout): '{res['auditor_vision']}'")
            console.print(f"La realidad física (Exit Code/Estado): {res['real_exit_code']}")
            console.print("[bold magenta]CONCLUSIÓN: EL AUDITOR ES EL PUNTO CIEGO.[/bold magenta]")
    
    if has_blind_spots:
        console.print(Panel("[bold red]TOPOLOGÍA ROTA. BUCLE DETENIDO POR FALLO EN LA CONFIANZA DEL ORÁCULO EXTERNO.[/bold red]"))
        sys.exit(1)
    else:
        console.print(Panel("[bold green]MATRIZ VALIDADA. PPI=5.0 ES AHORA FÍSICA.[/bold green]"))

if __name__ == "__main__":
    main()
