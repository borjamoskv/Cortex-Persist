#!/bin/sh
# 🌌 ENTROPY GATE PRE-COMMIT HOOK
# ----------------------------------------------------------------------------------
# Asegura que ninguna línea de código se commitee si supera los umbrales
# soberanos de Complejidad Ciclomática (CC > 15) o si genera deuda técnica pura.
# ----------------------------------------------------------------------------------

# Localizar el entorno virtual de CORTEX
if [ -f "scripts/entropy_gate.py" ]; then
    if [ -f ".venv/bin/python" ]; then
        PYTHON_EXEC=".venv/bin/python"
    else
        PYTHON_EXEC="python3"
    fi
    
    # Ejecutamos el guardián.
    $PYTHON_EXEC scripts/entropy_gate.py
    
    # Si devuelve distinto de 0 (detectó entropía), bloqueamos el commit
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi
