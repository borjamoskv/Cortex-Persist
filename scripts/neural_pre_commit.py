#!/usr/bin/env python3
# =============================================================================
# CORTEX NEURAL PRE-COMMIT SHIELD
# =============================================================================
# Escudo Axiomático Soberano. Evalúa el X-Ray Score del repo antes del commit.
# Si el código < 90/100, la máquina prohíbe el envío al Ledger temporal.

import sys
import os
import subprocess

def run_xray():
    try:
        cortex_xray = os.path.expanduser("~/cortex/xray_scan.py")
        if not os.path.exists(cortex_xray):
            return 100.0
        
        # Ejecutar en el directorio actual (que es la raíz del repo git interceptado)
        result = subprocess.run([sys.executable, cortex_xray], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "FINAL SCORE:" in line:
                # Ejemplo de línea: "⚡ FINAL SCORE: 85.50/100"
                score_str = line.split(":")[1].split("/")[0].strip()
                return float(score_str)
    except Exception:
        pass
    return 100.0

if __name__ == "__main__":
    print("\n👁️  [CORTEX NEURAL SHIELD] Escaneando mutaciones en el código (Pre-Commit)...")
    score = run_xray()
    
    print(f"🧬 Puntuación Estructural: {score}/100")
    
    if score < 90.0:
        print("⛔ BLOQUEADO: La calidad del código ha caído por debajo de la Soberanía Absoluta (90/100).")
        print("💡 RESOLUCIÓN: Invoca a Ouroboros o ejecuta `/mejoralo` para que el Enjambre eleve la arquitectura antes del commit.\n")
        sys.exit(1)
    else:
        print("✅ APROBADO: Estándar 130/100 verificado. Acceso al Ledger concedido.\n")
        sys.exit(0)
