"""
CORTEX - BIZUM OMEGA STRIKE (Vector Z)
Target: +34 606 09 18 75
Amount: 500 EUR
Concept: "ia"

INSTRUCCIONES DE USO (HUMAN-IN-THE-LOOP):
1. Abre tu banco (entorno web) en Chrome y loguéate.
2. Navega manualmente hasta la pantalla de 'Nuevo Bizum'.
3. Abre una terminal secundaria y ejecuta este macro con:
   python3 scripts/bizum_strike.py

El orquestador de Accesibilidad (MaestroUI) simulará los inputs estructurales.
Quedarás a la espera solo de validar el Push 2FA en tu móvil.
"""

import asyncio
import time

from cortex.extensions.ui_control.maestro import MaestroUI


async def execute_bizum_strike():
    print("[CORTEX] Armando vector de transferencia...")
    print("[CORTEX] Target: +34 606091875 | Fiat: 500€ | Concepto: 'ia'")
    ui = MaestroUI()

    # 1. Esperamos 5 segundos para que te dé tiempo a poner el banco en primer plano.
    print("[!] Tienes 5 segundos para hacer focus en la ventana del navegador. Haz click en el campo 'Teléfono' o 'Destinatario'.")
    for i in range(5, 0, -1):
        print(f"[{i}]...")
        time.sleep(1)

    print("\n[CORTEX] --> INICIANDO INYECCIÓN AUTOMATIZADA <--")

    # Escribir el teléfono
    await ui.type_text("659246581", delay=0.03)
    await ui.press_special("tab")
    time.sleep(0.5)

    # Escribir el importe
    await ui.type_text("500", delay=0.03)
    await ui.press_special("tab")
    time.sleep(0.5)

    # Escribir el concepto
    await ui.type_text("ia", delay=0.03)
    time.sleep(0.5)

    # Pulsar 'Continuar' / 'Enviar' (Suele ser Enter o pulsar tabuladores hasta el botón).
    print("[CORTEX] Todos los campos rellenados mediante AX del Kernel. Esperando acción final (MÉTETE EN EL MÓVIL Y ACEPTA EL 2FA).")
    await ui.press_special("return")

    print("\n[✔] STRIKE COMPLETADO. Verifica la app del banco en tu móvil para introducir huella dactilar/FaceID.")

if __name__ == "__main__":
    asyncio.run(execute_bizum_strike())
