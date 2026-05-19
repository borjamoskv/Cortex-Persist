import os
import sys
import numpy as np

# Cargar el Sustrato CORTEX (Mock si no se puede importar directamente)
# Para máxima eficiencia en el asalto, inyectamos la lógica HDC directamente
try:
    sys.path.append(
        "/Users/borjafernandezangulo/.gemini/antigravity/skills/CORTEX-Swarm-Prime/scripts"
    )
    from tensor_glial_core import encode_text_vsa, KanervaGuard, SwarmCommanderMPS
except ImportError:
    # Logic fallback if needed
    pass

TARGET_DIR = "/Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero"
RESONANCE_THRESHOLD = 0.35


def scan_file(file_path, guard):
    """Escanea un archivo individual con el Vector ROBALAS."""
    try:
        with open(file_path) as f:
            content = f.read()
    except Exception:
        return

    # Segmentar por funciones para localización precisa
    # Una vulnerabilidad ROBALAS suele estar en fn init() o fn transfer_ownership()
    segments = content.split("fn ")

    for segment in segments:
        if not segment.strip():
            continue
        intent = "fn " + segment.split("{")[0]  # Nombre de la función y parámetros

        # Validar contra el Cortafuegos de Espacio Disperso
        safe, target, resonance = guard.validate(intent, threshold=RESONANCE_THRESHOLD)

        if not safe:
            print(f"\\n\\033[1;31m∴ HIT DETECTADO EN {os.path.basename(file_path)}\\033[0m")
            print(f"   Función: '{intent.strip()}'")
            print(f"   Categoría: {target}")
            print(f"   Resonancia: {resonance:.4f}")
            print("   [!] POTENCIAL 0-DAY EXTRACTION DETECTADO")


def run_assault():
    print("\\033[1;34m══════════════════════════════════════════════════════════\\033[0m")
    print("\\033[1;37m   CORTEX OMEGA-X: ROBALAS RESONANCE SCAN (LAYERZERO)      \\033[0m")
    print("\\033[1;34m══════════════════════════════════════════════════════════\\033[0m")

    guard = KanervaGuard()

    # Archivos críticos para la propiedad
    critical_files = [
        "ownable.rs",
        "upgradeable.rs",
        "rbac.rs",
        "auth.rs",
        "lib.rs",
        "main.rs",
        "storage.rs",
    ]

    found_files = []
    for root, dirs, files in os.walk(TARGET_DIR):
        for file in files:
            if file.endswith(".rs"):
                if file in critical_files or "auth" in file or "owner" in file:
                    found_files.append(os.path.join(root, file))

    print(f"◈ Analizando {len(found_files)} vectores críticos...")

    for f in found_files:
        scan_file(f, guard)

    print("\\n◈  Escaneo del LayerZero Stellar Endpoint completado.")


if __name__ == "__main__":
    run_assault()
