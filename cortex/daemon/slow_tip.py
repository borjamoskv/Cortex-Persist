"""
slow_tip.py — Pedagogía de Latencia.

Provides contextual tips to the user during long-running CORTEX operations
(like REM phase maintenance or vector compaction). 
Inspired by the 'AESTHETIC TRUTH' axiom.
"""

import random

BIOLOGICAL_TIPS = [
    "CORTEX está en fase REM: compactando Songlines para optimizar tu memoria a largo plazo.",
    "El nivel de Cortisol digital está bajo. El agente opera con máxima claridad cognitiva.",
    "Sincronizando ritmos circadianos: la latencia actual es un subproducto de la auto-sanación.",
    "Dopamina sintética inyectada. Enjambre listo para la próxima ráfaga creativa.",
    "La autopoiesis está activa: reparando micro-fracturas en el ledger de transacciones.",
]

TECHNICAL_TIPS = [
    "Optimizando sqlite-vec: los vectores de 384 dimensiones requieren alineación térmica.",
    "Reduciendo entropía: eliminando fragmentos de memoria redundantes mediante Merkle Trees.",
    "Validando hash-chain: cada hecho se verifica contra su predecesor para garantizar integridad.",
    "Compacción de base de datos en curso. El espacio en disco es un recurso finito y sagrado.",
    "Soberanía digital: tus datos están encriptados con AES-GCM y verificados por CORTEX.",
]

def get_random_tip() -> str:
    """Return a random tip from either biological or technical categories."""
    all_tips = BIOLOGICAL_TIPS + TECHNICAL_TIPS
    return random.choice(all_tips)

def get_contextual_tip(category: str) -> str:
    """Return a tip from a specific category ('biological' or 'technical')."""
    if category == "biological":
        return random.choice(BIOLOGICAL_TIPS)
    return random.choice(TECHNICAL_TIPS)
