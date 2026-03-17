#!/usr/bin/env python3
import hashlib
import os
import subprocess
import time

# Path of the design tokens (e.g., inside Naroa)
TOKENS_PATH = os.path.expanduser("~/game/naroa-2026/css/tokens.css")


def get_hash(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()  # nosec — SHA-256 replaces MD5


def watch_tokens():
    print("🕸️ AETHER-STITCH INICIADO: Monitoreando Design Tokens (Google Stitch vs OSS)")
    print(f"👁️ Observando: {TOKENS_PATH}")

    current_hash = get_hash(TOKENS_PATH)

    try:
        while True:
            time.sleep(2)
            new_hash = get_hash(TOKENS_PATH)

            if current_hash != new_hash and new_hash != "":
                print("\n[AETHER-STITCH] ⚠️ Alteración estructural de diseño detectada!")
                print("Lanzando agente de compilación e inspección Visual Noir (130/100)...")

                # Integración con Ouroboros o Gemini (CLI) — safe subprocess call
                prompt = (
                    f"Visualiza los cambios en {TOKENS_PATH}. "
                    "¿Son compatibles con la estética Industrial Noir? "
                    "Devuelve un rating 130/100 y re-compila el CSS si hace falta."
                )
                subprocess.run(["gemini", prompt, "-y"], check=False)  # nosec B603

                current_hash = new_hash
                print("\n[AETHER-STITCH] ✨ Re-sincronización de variables completada.")
                print("----------------------------------------------------------")

    except KeyboardInterrupt:
        print("\nAETHER-STITCH daemon apagado.")


if __name__ == "__main__":
    watch_tokens()
