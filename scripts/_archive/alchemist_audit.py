import asyncio
import os
import sys

# Agregamos cortex al path
sys.path.insert(0, os.path.expanduser("~/cortex"))

from cortex.engine import CortexEngine


async def main():
    async with CortexEngine() as engine:
        print("🧪 [ALQUIMISTA] Iniciando Auditoría de Fantasmas...")

        # Ident IDs de los ghosts encontrados en el triage previo
        ghost_ids = [4217, 4218, 4219]

        # 1. Crear el Hecho Consolidado (Ω₂)
        content = (
            "DECISIÓN: Consolidación de Fantasmas de Sistema. "
            "Los proyectos ARCHIVE_MISC, BORJAMOSKV y CORTEX se establecen en estado de Homeostasis. "
            "Se eliminan los punteros 'desconocidos' (Ghosts) para densificar el grafo semántico y "
            "acelerar el InfiniteMindsManager (Antientropía Ω₂)."
        )

        new_fact_id = await engine.store(
            project="GLOBAL",
            content=content,
            fact_type="decision",
            tags=["alchemist", "antientropy", "consolidation", "homeostasis"],
            confidence="C5",
            source="agent:alquemista:antigravity",
        )

        print(f"✅ Hecho de Consolidación creado [ID:{new_fact_id}]")

        # 2. Conectar y Deprecar Ghosts
        for gid in ghost_ids:
            try:
                await engine.deprecate(
                    gid, reason=f"Consolidado en Hecho #{new_fact_id} (Operación Antientrópica)"
                )
                print(f"💀 Ghost #{gid} conectado y archivado.")
            except Exception as e:
                print(f"⚠️ Error al deprecar ghost #{gid}: {e}")

        print("\n✨ Auditoría completada. El espacio de búsqueda semántica ha sido optimizado.")


if __name__ == "__main__":
    asyncio.run(main())
