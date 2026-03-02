#!/usr/bin/env python3
"""
VOID-WATCHER DAEMON 👁️
The Sovereign Monitor of Architectural Entropy.

Operation:
1. Passively scans Python projects for cognitive complexity (McCabe) and Maintainability Index (MI).
2. Uses Radon under the hood.
3. If files cross the "Static" threshold (high complexity, low maintainability),
   triggers macOS notifications and logs to CORTEX.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
except ImportError:
    print("❌ Void-Watcher requiere 'radon'. Instálalo con: pip install radon")
    sys.exit(1)

# --- THRESHOLDS SOBERANOS (Axioma 14) ---
# Complejidad Ciclomática: F > 10 es "Estática"
CC_THRESHOLD = 15  
# Maintainability Index: < 20 es peligroso
MI_THRESHOLD = 20  
# Intervalo de escaneo (segundos) - 5 min
SCAN_INTERVAL = 300 

def send_macos_notification(title: str, subtitle: str, message: str):
    """Envía una notificación nativa en macOS vía AppleScript."""
    script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
    subprocess.run(["osascript", "-e", script])

def get_python_files(directory: Path):
    """Obtiene todos los archivos .py ignorando venvs y dirs ocultos."""
    for root, dirs, files in os.walk(directory):
        # Filtrar dotfiles y entornos virtuales
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '.venv', 'node_modules', '__pycache__')]
        for file in files:
            if file.endswith('.py'):
                yield Path(root) / file

def scan_file_entropy(filepath: Path) -> dict:
    """Escanea un único archivo y devuelve métricas de entropía."""
    try:
        with open(filepath, encoding='utf-8') as f:
            code = f.read()
            
        # 1. Complexity
        blocks = cc_visit(code)
        # Promedio complejidad de las funciones/clases en este archivo
        cc_scores = [block.complexity for block in blocks]
        avg_cc = sum(cc_scores) / len(cc_scores) if cc_scores else 0
        max_cc = max(cc_scores) if cc_scores else 0
        
        # 2. Maintainability Index
        mi_score = mi_visit(code, multi=False)
        
        return {
            'filepath': filepath,
            'avg_cc': avg_cc,
            'max_cc': max_cc,
            'mi': mi_score
        }
    except Exception:
        # Silently ignore parsing errors
        return None

def analyze_project(directory: Path):
    """Analiza un proyecto completo e identifica entropía crítica."""
    print(f"👁️  VOID-WATCHER {time.strftime('%H:%M:%S')} | Escaneando {directory.name}...")
    
    critical_files = []
    total_files = 0
    
    for py_file in get_python_files(directory):
        total_files += 1
        metrics = scan_file_entropy(py_file)
        if metrics:
            if metrics['max_cc'] >= CC_THRESHOLD or metrics['mi'] <= MI_THRESHOLD:
                critical_files.append(metrics)
                
    if critical_files:
        print(f"⚠️  Detección: {len(critical_files)} archivos con entropía hiper-densa.")
        
        # Top offender
        critical_files.sort(key=lambda x: x['max_cc'], reverse=True)
        top_offender = critical_files[0]
        name = top_offender['filepath'].name
        cc = top_offender['max_cc']
        mi = top_offender['mi']
        
        msg = f"Archivo crítico: {name} (CC: {cc}, MI: {mi:.1f})"
        print(f"   ► {msg}")
        
        # Enviar notificación si es muy grave
        send_macos_notification(
            title="🌌 VOID-WATCHER: Alerta de Entropía",
            subtitle=f"Proyecto: {directory.name}",
            message=f"Se detectó estática grave en {len(critical_files)} archivos. Peor ofensor: {name} (CC={cc}). Considere /void-omega."
        )
    else:
        print(f"✅ Arquitectura respirando correctamente. {total_files} archivos sanos.")

def main():
    target_dir = Path.cwd()
    single_run = False
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == '--single-run':
                single_run = True
            else:
                target_dir = Path(arg).resolve()
        
    print(f"👁️  Iniciando VOID-WATCHER Daemon en {target_dir}")
    print(f"   Métricas: CC > {CC_THRESHOLD} (Peligro) | Ley de Landauer activa.")
    if not single_run:
        print("   Presiona Ctrl+C para detener monitoring.\n")
    else:
        print("   [Modo Single-Run activo: Un solo escaneo]\n")
    
    send_macos_notification(
        "👁️ VOID-WATCHER Activo",
        "El Demonio Soberano está vigilando.",
        f"Monitoreando entropía en: {target_dir.name}"
    )
    
    try:
        while True:
            # Check solo si hay modificaciones recientes sería ideal, pero por ahora escaneamos todo
            analyze_project(target_dir)
            if single_run:
                break
            time.sleep(SCAN_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 VOID-WATCHER detenido por el operador.")

if __name__ == "__main__":
    main()
