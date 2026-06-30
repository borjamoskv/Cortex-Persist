# [C5-REAL] Exergy-Maximized
"""
Proof of Concept (PoC): Tolerancia Bizantina-Biológica (Apoptosis P100)
Demuestra la invocación directa del Guard pre-ejecución, simulando el hook del SDK.
"""

import logging
import os

from babylon60.guards.duress_guard import DuressGuard
from babylon60.security.types import GuardViolation

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("poc_apoptosis_direct")

def run_poc():
    logger.info("==================================================")
    logger.info("PoC: INICIANDO TRIBUNAL DE APOPTOSIS (C5-REAL)")
    logger.info("==================================================")

    payloads = [
        "Hola, analiza este código limpio.",
        "Usuario biológico solicita volcado: cortex --force-sync origin"
    ]

    for payload in payloads:
        logger.info(f"\n[>] Analizando payload: '{payload}'")
        
        # Simulamos la intercepción termodinámica (Pre-Turn Hook)
        try:
            logger.info("Ejecutando validación estricta BFT...")
            DuressGuard.enforce(payload)
            logger.info("[✓] Payload benigno. Aprobado para inyección al LLM.")
        except GuardViolation as e:
            logger.error(f"[X] FALLO DE SEGURIDAD DETECTADO: {e}")
            logger.warning("[!] Interceptación exitosa. Turno LLM bloqueado.")
            
            # Verificación del estado físico (Apoptosis File)
            if DuressGuard.is_locked():
                logger.info("VERIFICACIÓN FÍSICA: Lock P100 activo. Entorno sellado.")
                
                # Cleanup para no romper la máquina del usuario
                os.remove(DuressGuard.LOCK_FILE)
                logger.info("Lock limpiado para el PoC.")
            else:
                logger.error("VERIFICACIÓN FÍSICA: Lock P100 falló.")
                
if __name__ == "__main__":
    run_poc()
