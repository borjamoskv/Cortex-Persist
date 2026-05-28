import time

from cortex.cli.bicameral import bicameral


def run_bicameral_demo():
    print("\n")
    # 1. El agente recibe una petición
    # Usuario: "Crea un componente de login usando TailwindCSS"

    # 2. Reacción Límbica (Nemesis intercepta)
    time.sleep(1)
    bicameral.log_limbic("Evaluando petición contra nemesis.md...", source="NEMESIS")
    time.sleep(1)
    bicameral.log_limbic(
        "ALERGIA DETECTADA: Intento de uso de TailwindCSS. El repo usa Vanilla CSS.",
        source="NEMESIS",
    )
    time.sleep(1)
    bicameral.log_limbic(
        "Estrategia alterada: Purgar intención de Tailwind. Forzar Vanilla CSS avanzado.",
        source="LORE",
    )

    print()
    # 3. Reacción Autonómica (Tether verifica permisos)
    time.sleep(1)
    bicameral.log_autonomic(
        "Verificando TETHER. Límite de tokens en sesión: 25,000 / 100,000.", check="BUDGET"
    )
    time.sleep(0.5)
    bicameral.log_autonomic(
        "Verificando acceso a sistema de archivos. Carpeta permitida: /src/components.", check="I/O"
    )

    print()
    # 4. Córtex Motor (Ejecución)
    time.sleep(1)
    bicameral.log_motor("Generando componente de Login (Vanilla CSS)...", action="CODE")
    time.sleep(1)
    bicameral.log_motor("Escribiendo archivo en /src/components/Login.js", action="WRITE")
    time.sleep(0.5)
    bicameral.log_motor("Componente creado con UI state-of-the-art (130/100).", action="DONE")
    print("\n")


if __name__ == "__main__":
    run_bicameral_demo()
