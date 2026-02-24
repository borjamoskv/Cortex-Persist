import time

from cortex.cli.bicameral import bicameral


def run_swarm_demo():
    print("\n")
    # 1. El Orquestador evalúa la magnitud
    time.sleep(1)
    bicameral.log_motor(
        "Petición: Refactor masivo de 50 archivos (Arquitectura Hexagonal).", action="SCOPE"
    )
    time.sleep(1)
    bicameral.log_autonomic(
        "Evaluación de recursos: Requiere Enjambre (>10 archivos).", check="CAPACITY"
    )

    print("\n" + "═" * 80)
    print(" ⧖ PROTOCOLO LEGION-1 INICIADO: CLONACIÓN DE LINAJE")
    print("═" * 80 + "\n")

    # 2. Síntesis del Linaje
    time.sleep(1)
    bicameral.log_limbic("Sintetizando soul.md, lore.md y nemesis.md...", source="GENESIS")
    time.sleep(1)
    bicameral.log_limbic(
        "Empaquetando 14 alergias operativas y 3 cicatrices críticas.", source="GENESIS"
    )
    time.sleep(0.5)
    bicameral.log_motor("Exportando -> cortex_bloodline_091.json", action="BUILD")

    print("\n" + "─" * 40)
    # 3. Despliegue del Enjambre (Workers naciendo con contexto)
    time.sleep(1)
    for i in range(1, 4):
        print(f"[⚡] Instanciando Worker-0{i} [Modelo: Flash] [Contexto: Bloodline_091]")
        time.sleep(0.2)

    print("─" * 40 + "\n")

    # 4. Prueba del Linaje Heredeado
    time.sleep(1)
    bicameral.log_limbic(
        "Worker-02 reporta: Detectada inyección de dependencias errónea. Abortando por regla Nemesis-04.",
        source="SWARM",
    )
    time.sleep(1)
    bicameral.log_limbic(
        "Worker-03 reporta: Refactor completado esquivando error de concurrencia gracias a Cicatriz ep_0042.",
        source="SWARM",
    )

    print("\n" + "═" * 80)
    print(" ⧖ CONSENSO BIZANTINO ALCANZADO | ENJAMBRE DISUELTO")
    print("═" * 80 + "\n")

    # 5. Cierre Motor
    time.sleep(1)
    bicameral.log_motor("Merge final completado con éxito. Ninguna regla rota.", action="DONE")
    print("\n")


if __name__ == "__main__":
    run_swarm_demo()
