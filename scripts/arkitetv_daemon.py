import ast
import time
import os
import subprocess
import itertools
from pathlib import Path
from datetime import datetime

# ==============================================================================
# ARKITETV DAEMON - The Structural Sentinel
# ==============================================================================
# Daemon soberano que monitorea la entropía del sistema en tiempo real.
# Detecta files sobredimensionados, alta complejidad y acoplamiento fantasma.
# 150/100 by Default: Si la entropía sube, persiste un Ghost en CORTEX e
# informa al operador (macOS Notification).
# ==============================================================================

PROJECT_NAME = "cortex"
# Directorio a monitorear (se puede parametrizar)
TARGET_DIR = Path(os.path.expanduser("~/cortex/cortex"))
CORTEX_CLI_PATH = Path(os.path.expanduser("~/cortex/.venv/bin/python"))

# --- Limits & Thresholds (Industrial Noir Standards) ---
MAX_LINES_OF_CODE = 400
COMPLEXITY_THRESHOLD = 15  # Max num of if/for/while per file
OVERLAP_THRESHOLD = 0.50   # 50% info overlap implies shadow coupling
CHECK_INTERVAL_SEC = 300   # 5 minutos


def notify_macos(title: str, text: str):
    """Notificación nativa en macOS (Industrial Noir Style)."""
    script = f'display notification "{text}" with title "{title}" subtitle "⚡ ARKITETV Daemon"'
    subprocess.run(["osascript", "-e", script])


def persist_ghost(content: str):
    """Guarda un fantasma anatómico directo en la memoria CORTEX."""
    try:
        cmd = [
            str(CORTEX_CLI_PATH),
            "-m", "cortex.cli", "store",
            "--type", "ghost",
            "--source", "daemon:arkitetv",
            PROJECT_NAME,
            content
        ]
        subprocess.run(cmd, cwd=os.path.expanduser("~/cortex"), capture_output=True)
    except Exception as e:
        print(f"Error persisting ghost: {e}")


def analyze_file_ast(filepath: Path) -> dict:
    """Extrae métricas topológicas de un fichero Python via AST."""
    metrics = {"lines": 0, "complexity": 0, "identifiers": set()}
    
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        metrics["lines"] = len(source.splitlines())
    except Exception:
        return metrics

    for node in ast.walk(tree):
        # Complejidad Ciclomática / Ramificación Estructural
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler, ast.With)):
            metrics["complexity"] += 1
            
        # Nube léxica para Shadow Coupling
        if isinstance(node, ast.Name):
            metrics["identifiers"].add(node.id)
        elif isinstance(node, ast.arg):
            metrics["identifiers"].add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            metrics["identifiers"].add(node.name)
        elif isinstance(node, ast.Attribute):
            metrics["identifiers"].add(node.attr)

    return metrics


def calculate_overlap(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    return len(intersection) / min(len(set_a), len(set_b))


def run_entropy_scan():
    """Ejecuta un barrido profundo de entropía estructural."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando escaneo de entropía estructural...")
    
    files = list(TARGET_DIR.rglob("*.py"))
    ast_data = {}
    
    # 1. Escaneo Individual (Densidad y Complejidad)
    for f in files:
        if "venv" in f.parts or "test" in f.name or "migrations" in f.parts:
            continue
            
        metrics = analyze_file_ast(f)
        rel_path = f.relative_to(TARGET_DIR.parent)
        
        ast_data[str(rel_path)] = metrics["identifiers"]
        
        # Infracciones Estructurales
        infracciones = []
        if metrics["lines"] > MAX_LINES_OF_CODE:
            infracciones.append(f"Masa Crítica excedida ({metrics['lines']} LOC).")
        if metrics["complexity"] > COMPLEXITY_THRESHOLD:
            infracciones.append(f"Densidad Ciclomática alta ({metrics['complexity']} nodos de ramificación).")
            
        if infracciones:
            msg = f"{str(rel_path)} requiere re-estructuración. " + " | ".join(infracciones)
            print(f"⚠️ Detección: {msg}")
            notify_macos("Entropía Estructural Detectada", msg)
            persist_ghost(f"Architectural intervention required in {rel_path}. Reasons: {', '.join(infracciones)}")

    # 2. Escaneo de Ecosistema (Acoplamiento Fantasma / Shadow Dependencies)
    file_list = list(ast_data.keys())
    high_coupling = []
    
    for f1, f2 in itertools.combinations(file_list, 2):
        overlap = calculate_overlap(ast_data[f1], ast_data[f2])
        if overlap > OVERLAP_THRESHOLD:
            high_coupling.append((overlap, f1, f2))
            
    for score, f1, f2 in sorted(high_coupling, reverse=True, key=lambda x: x[0])[:3]:
        msg = f"Acoplamiento del {int(score*100)}% entre \n{f1} y {f2}."
        print(f"🔗 Shadow Dependency: {msg}")
        notify_macos("Fusión Estructural Peligrosa", msg)
        persist_ghost(f"High mutual information / Shadow Coupling detected ({int(score*100)}%) between {f1} and {f2}. Disentangle concepts.")


def main():
    print("=====================================================")
    print(" Ojo del Demiurgo / ARKITETV-DAEMON Activado         ")
    print(f" Target: {TARGET_DIR}")
    print("=====================================================")
    
    # Notificación inicial
    notify_macos("ARKITETV Daemon Offline->Online", "Monitoreando entropía y deuda técnica.")
    
    while True:
        try:
            run_entropy_scan()
        except Exception as e:
            print(f"Error durante escaneo: {e}")
        
        # Suspensión criogénica hasta el siguiente ciclo
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
