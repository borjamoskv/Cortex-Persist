"""
[C5-REAL] Exergy-Maximized
Φ4 - Oráculo Externo Mínimo (Testigo) & Fuzzing Semántico
Inyección de entropía en la lógica del auditor para colapsar Unknown Unknowns asintóticos.
"""

import ast
import random
import subprocess
import sys

from rich.console import Console

console = Console()


class SemanticMutator(ast.NodeTransformer):
    """Mutador semántico a nivel AST para inyectar fallos (Chaos Engineering) en el propio código auditor."""

    def __init__(self):
        self.mutations_applied = 0

    def visit_Compare(self, node):
        """Mutate comparisons: == to !=, etc. para romper la lógica del auditor."""
        if random.random() < 0.3:
            for i, op in enumerate(node.ops):
                if isinstance(op, ast.Eq):
                    node.ops[i] = ast.NotEq()
                    self.mutations_applied += 1
                elif isinstance(op, ast.NotEq):
                    node.ops[i] = ast.Eq()
                    self.mutations_applied += 1
        return self.generic_visit(node)


def generate_mutant(source_file, target_file):
    """Lee el script S, lo muta semánticamente y escribe la versión mutante."""
    with open(source_file) as f:
        source_code = f.read()

    tree = ast.parse(source_code)
    mutator = SemanticMutator()
    mutated_tree = mutator.visit(tree)
    ast.fix_missing_locations(mutated_tree)

    with open(target_file, "w") as f:
        f.write(ast.unparse(mutated_tree))

    return mutator.mutations_applied


def run_oracle(mutant_path):
    """
    Φ4: El Oráculo Mínimo Externo ejecuta el mutante.
    Mide si el sistema es frágil a su propia lógica de auditoría mutada.
    """
    try:
        process = subprocess.run(
            [sys.executable, mutant_path], capture_output=True, text=True, timeout=5
        )
        return process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def main():
    target_script = "cortex/forensics/self_audit_loop.py"
    mutant_script = "cortex/forensics/_mutant_audit.py"

    console.print("[bold cyan]INICIANDO Φ4: FUZZING SEMÁNTICO Y ORÁCULO EXTERNO[/bold cyan]")

    mutations = generate_mutant(target_script, mutant_script)
    console.print(f"[dim]Mutaciones aplicadas al AST de {target_script}: {mutations}[/dim]")

    if mutations > 0:
        console.print("[yellow]Ejecutando oráculo externo contra el mutante...[/yellow]")
        code, out, err = run_oracle(mutant_script)

        # El Oráculo (nosotros, desde fuera del mutante) evalúa el resultado
        console.print(f"Exit Code del Mutante: {code}")

        if code == 0:
            console.print(
                "[bold red]CRITICAL: El mutante sobrevivió e informó éxito. Unknown Unknown de lógica materializado.[/bold red]"
            )
        else:
            console.print(
                "[bold green]El mutante colapsó (Exit != 0). El sistema detectó la corrupción de la lógica de auditoría.[/bold green]"
            )
    else:
        console.print(
            "[dim]No se generaron mutaciones. Entropía insuficiente en esta iteración.[/dim]"
        )


if __name__ == "__main__":
    main()
