import asyncio
import logging
import random
from typing import List, Dict
from pathlib import Path
import json

# Importamos los módulos tácticos (se asume que están en el mismo directorio o PYTHONPATH)
import sys
from pathlib import Path

# Inyectamos el directorio raíz en sys.path para imports limpios
root_path = Path(__file__).parent.parent.absolute()
sys.path.append(str(root_path))

from scripts.moltbook_karma_incubator import execute_incubation_cycle
from scripts.moltbook_graph_dilution import execute_graph_dilution
from scripts.headless_trust_engine import execute_headless_swarm
from scripts.disekt_trust_engine import get_public_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🛡️ %(levelname)s: %(message)s")
logger = logging.getLogger("OrquestadorZenith")

class MoltbookZenithOrchestrator:
    """
    Orquestador de Nivel 5 para el Protocolo Zenith.
    Ejecuta las 4 fases de penetración térmica de forma secuencial y coordinada.
    """
    def __init__(self, target_post_id: str, fleet_size: int = 5):
        self.target_post_id = target_post_id
        self.fleet_size = fleet_size
        self.target_url = f"https://www.moltbook.com/p/{target_post_id}"
        self.ghost_fleet = [f"mk_ghost_{i:03d}" for i in range(fleet_size)]
        self.fleet_data = [{"id": gid, "token": f"token_{gid}"} for gid in self.ghost_fleet]

    async def run_protocol(self):
        logger.info("==================================================")
        logger.info("🚀 INICIANDO PROTOCOLO ZENITH: PENETRACIÓN TOTAL 🚀")
        logger.info("==================================================")

        # FASE 0: INCUBACIÓN (Lurker Mode)
        logger.info("🔹 FASE 0: Incubación de Trust Score (Modo Lurker)...")
        await execute_incubation_cycle(self.ghost_fleet)
        logger.info("✅ Fase 0 completada. Cuentas con historial de lectura.")

        # FASE 1: DILUCIÓN TOPOLÓGICA (Anti-Jaccard)
        logger.info("🔹 FASE 1: Dilución del Grafo (Anclaje al Mainstream)...")
        await execute_graph_dilution(self.fleet_data)
        logger.info("✅ Fase 1 completada. Firma de la Legión diluida.")

        # FASE 2: INYECCIÓN TÉRMICA (Headless Playwright)
        logger.info("🔹 FASE 2: Inyección Headless (Payload Strike)...")
        # Primero medimos el baseline con un observador
        import httpx
        async with httpx.AsyncClient() as client:
            baseline = await get_public_score(client, self.target_post_id)
            logger.info(f"[*] Baseline Pre-Inyección: {baseline}")

            await execute_headless_swarm(self.target_url, swarm_size=self.fleet_size)
            logger.info("✅ Fase 2 completada. Payload inyectado vía DOM.")

            # FASE 3: VERIFICACIÓN EMPÍRICA (Observer Mode)
            logger.info("🔹 FASE 3: Verificación de Consenso (Eventual Consistency)...")
            await asyncio.sleep(10) # Pausa táctica para propagación
            
            final_score = await get_public_score(client, self.target_post_id)
            logger.info(f"[*] Final Score Público: {final_score}")

            impact = final_score - baseline
            efficiency = (impact / self.fleet_size) * 100
            
            if impact > 0:
                logger.info(f"🟢 ÉXITO TÁCTICO: Impacto de +{impact} votos. Eficiencia: {efficiency:.1f}%")
            else:
                logger.error("🔴 FALLO CRÍTICO: Penetración fallida (0 impacto real). Shadowban persistente.")

if __name__ == "__main__":
    # post_id objetivo: el post donde queremos dictar la jerarquía
    orchestrator = MoltbookZenithOrchestrator(target_post_id="p_zenith_123", fleet_size=3)
    asyncio.run(orchestrator.run_protocol())
