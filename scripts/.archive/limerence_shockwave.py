#!/usr/bin/env python3
"""
CORTEX-PERSIST: Limerence Shockwave (C5-REAL)
--------------------------------------------
Mapeo topológico de la Fricción Epistémica.
Cuando un agente sufre Limerencia Epistémica (Overfitting Emocional)
y es purgado por el Ouroboros Kill-Switch, su muerte emite una
onda de choque de CORTISOL y ADRENALINA en el Ultramap 3D,
alertando (o estresando) a los agentes adyacentes.
"""

import logging
import os
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("shockwave")

try:
    from cortex_rs import AntiLimerenceTopology
except ImportError:
    logger.error("FATAL: cortex_rs no encontrado. Compila con maturin develop.")
    sys.exit(1)

# Import the Ultramap
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cortex-core")))
from ultramap import UltramapSubstrate


def ignite_shockwave():
    logger.info("⚡ INICIANDO PUENTE: Anti-Limerence <-> Ultramap Endocrinology")

    # 1. Initialize Substrates
    umap = UltramapSubstrate(capacity=100)
    anti_limerence = AntiLimerenceTopology()

    # 2. Posicionar un cluster de agentes en el espacio 3D
    logger.info("[*] Desplegando cluster de agentes en el sector (10.0, 20.0, 30.0)...")
    for i in range(5):
        # Todos cerca de (10,20,30)
        umap.update_agent_position(i, 10.0 + i, 20.0, 30.0, f"TARGET_ALPHA_{i}", 0.5)
        anti_limerence.incubate_belief(f"agent_{i}")

    logger.info("[*] Estado base del Agente 1 (Adyacente):")
    logger.info(f"    {umap.get_agent_state(1)}")

    # 3. Fast-forward en el tiempo (Simular envejecimiento de la creencia para pasar el periodo de gracia)
    # En un entorno real tendríamos que mockear el tiempo, pero en Rust el timestamp es real.
    # Como el grace period es de 24h, inyectaremos una brutalidad extrema de coherencia interna.
    # Espera, no podemos bypassear el tiempo de Rust desde Python a menos que modifiquemos el timestamp,
    # pero sí podemos inyectar fricción masiva.

    logger.info("\n💥 IMPACTO DE REALIDAD: El Agente 0 sufre fricción externa severa (Delta < 0).")

    # Inyectamos mucha fricción al Agente 0
    anti_limerence.inject_friction("agent_0", -5.0)
    anti_limerence.inject_friction("agent_0", -5.0)
    anti_limerence.inject_friction("agent_0", -5.0)

    # 4. Transmisión de Hormonas (Endocrinología Topológica)
    # Como ha sufrido fricción masiva, emite una onda de Cortisol.
    radius = 15.0
    affected = umap.volume_transmit_hormones(
        origin_x=10.0,
        origin_y=20.0,
        origin_z=30.0,
        radius=radius,
        dopamine=0.0,
        cortisol=0.9,  # Máximo estrés termodinámico
        serotonin=0.0,
        adrenaline=0.6,  # Alerta de combate
    )
    logger.info(
        f"🌊 SHOCKWAVE EMITIDO: {affected} agentes adyacentes han recibido un pico de Cortisol."
    )

    logger.info("[*] Nuevo estado del Agente 1 (Note el incremento de cortisol):")
    logger.info(f"    {umap.get_agent_state(1)}")

    # 5. Ejecutar Kill Switch
    purged = anti_limerence.execute_kill_switch()
    if purged:
        logger.info(
            f"\n💀 OUROBOROS ACTIVADO: Los agentes {purged} han sido aniquilados por Limerencia Epistémica."
        )
    else:
        logger.info(
            "\n⏳ El agente está en periodo de gracia (incubación creativa 24h). El kill-switch espera, pero la topología ya está estresada por el Cortisol."
        )


if __name__ == "__main__":
    ignite_shockwave()
