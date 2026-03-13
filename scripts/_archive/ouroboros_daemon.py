#!/usr/bin/env python3
"""
CORTEX OUROBOROS-Ω Daemon.
The serpent that eats its own tail. 
Continuously scans the CORTEX codebase via AST parsing, identifies functions 
with extreme cyclomatic complexity (entropic rot), and autonomously enqueues 
TESSERACT-Ω / Aether tasks to refactor and decouple itself in O(1).
"""

import os
import ast
import subprocess
import time
from pathlib import Path

def get_python_files(root_dir):
    """Recursively yield all python files excluding virtual environments."""
    for path in Path(root_dir).rglob('*.py'):
        if '.venv' not in path.parts and '__pycache__' not in path.parts and '.tox' not in path.parts:
            yield path

def calculate_complexity(node):
    """Calculate an approximate McCabe cyclomatic complexity via AST traversal."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Lambda, ast.Call, ast.BoolOp)):
            complexity += 1
    return complexity

def run_ouroboros():
    cortex_dir = os.path.expanduser("~/.gemini/antigravity/scratch/Cortex-Persist")
    print("\033[38;5;127m[OUROBOROS-Ω]\033[0m Iniciando disección del Árbol de Sintaxis Abstracta (AST) de MOSKV-CORTEX...")
    
    worst_file = None
    worst_complexity = 0
    worst_func = None
    
    for py_file in get_python_files(cortex_dir):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(py_file))
                
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    comp = calculate_complexity(node)
                    if comp > worst_complexity:
                        worst_complexity = comp
                        worst_file = py_file
                        worst_func = node.name
        except (SyntaxError, UnicodeDecodeError, ValueError, OSError) as e:
            # Explicit warning instead of silent ignore
            print(f"\\033[38;5;127m[OUROBOROS-Ω]\\033[0m ⚠️  Ignorando archivo corrupto o ilegible {py_file!r}: {e}")
            continue
    # Threshold for unacceptable entropy is 15
    if worst_file and worst_complexity >= 15:
        print(f"\n\033[38;5;127m[OUROBOROS-Ω]\033[0m ⚠️ ANOMALÍA ESTRUCTURAL CRÍTICA DETECTADA")
        print(f"   Target: \033[1m{worst_file.relative_to(cortex_dir)}:{worst_func}\033[0m")
        print(f"   Gravedad Entrópica: \033[38;5;196m{worst_complexity} CC\033[0m (Vulnera Axioma 2: Asimetría Entrópica)")
        print("\n\033[38;5;154m[OUROBOROS-Ω]\033[0m Autogenerando misión de auto-destrucción y re-forjado...")
        
        # Enqueue the task
        subprocess.run([
            os.path.join(cortex_dir, ".venv", "bin", "python"), "-m", "cortex.aether.cli", "enqueue",
            str(worst_file.parent),
            f"Ouroboros Refactor: {worst_file.name}:{worst_func}",
            "-d", f"La función `{worst_func}` ha superado el límite legal de complejidad (CC={worst_complexity}). Disecciona su flujo, extrae helpers inmutables y refactoriza esta atrocidad para cumplir O(1) o Muerte. Esta es una orden de Ouroboros-Omega."
        ], cwd=cortex_dir, check=False)
        print("\033[38;5;154m[OUROBOROS-Ω]\033[0m La serpiente muerde su cola. Misión inyectada. Tesseract convergerá el código en O(1).\033[0m")
    else:
        print("\033[38;5;154m[OUROBOROS-Ω]\033[0m Entropía estructural bajo control absoluto. Sistema biológicamente estable.\033[0m")

if __name__ == "__main__":
    run_ouroboros()
