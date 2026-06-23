#!/usr/bin/env python3
"""
cortex/nodes/mtk_stress_test.py
Prueba de carga termodinámica sobre el MTK.
Intentaremos inyectar un payload masivamente estocástico (100 claims, 0 evidencia).
"""

import asyncio
import os
from datetime import datetime, timezone

# Falsificar el testing enviroment para no romper librerías
os.environ["CORTEX_TESTING"] = "1"

from babylon60.engine.mtk_core import MTKGuard
from babylon60.types.evidence import ClosurePayload, EvidenceBundle


async def run_entropy_test():
    print("🧪 Iniciando Stress Test Termodinámico sobre MTK...")
    
    # Simular evidencia nula
    evidence = EvidenceBundle.forge(
        query="Generación probabilística masiva",
        sources=[],  # Cero fuentes (Precisión = 0)
        retrieved_at=datetime.now(timezone.utc)
    )
    
    # Simular alta complejidad (100 aserciones)
    claims = [{"claim": f"Alucinación {i}"} for i in range(100)]
    
    print(f"📊 Evaluando Payload: {len(claims)} aserciones, {len(evidence.sources)} fuentes empíricas.")
    
    payload = ClosurePayload.seal(
        claims=claims,
        evidence=evidence,
        verdict=True,
        info_exergy=1.0 # Exergía base aparente
    )
    
    # Instanciar el MTK Guard
    private_key = os.environ.get("CORTEX_KERNEL_KEY", "dummy_key_for_test")
    guard = MTKGuard(private_key=private_key)
    
    print("🚧 Cruzando el límite de transacción MTK...")
    try:
        async with guard.transaction_boundary(payload) as token:
            print(f"❌ FALLO ESTRUCTURAL: El MTK emitió el token {token} para un payload entrópico.")
    except ValueError as e:
        if "MTK-REJECT" in str(e):
            print("✅ EXITO (Szilard Engine Gate): El MTK interceptó y aniquiló la anergía.")
            print(f"🛡️ Detalle del Bloqueo: {e}")
        else:
            print(f"⚠️ Error desconocido: {e}")

if __name__ == "__main__":
    asyncio.run(run_entropy_test())
