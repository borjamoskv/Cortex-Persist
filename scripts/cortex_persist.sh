#!/bin/bash
cd ~/cortex

echo "Persistiendo decisión arquitectónica en CORTEX..."
.venv/bin/python -m cortex.cli store --type decision cortex "UBERMIND-OMEGA: Erradicó bare exceptions genéricas y transmuto a excepciones arquitectónicas (sqlite3.Error, OSError, ValueError) en scripts de terminal y comandos CLI (tips, reflect, launchpad, trust, vote) para elevar higiene a 130/100."

echo "Persistiendo error y resolución en CORTEX..."
.venv/bin/python -m cortex.cli store --type error cortex "ERROR: Blanketing try/except en la suite CLI y scripts bridges (silencing fallos nativos). FIX: Reemplazos puristas por tipos de error deterministas detectados por X-Ray 13D."

echo "Exportando snapshot CORTEX actualizado..."
.venv/bin/python -m cortex.cli export

echo "✅ FASE 6 (Persistencia) Completada Exitosamente."
