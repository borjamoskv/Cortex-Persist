import json
import logging
import os


# Configuración de logs Industrial Noir
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [STRIPE-LIVE] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_live_status():
    print("\n" + "="*60)
    print(" CORTEX PERSIST — STRIPE LIVE ACTIVATION PIPELINE ")
    print("="*60 + "\n")

    env_file = ".env"
    if not os.path.exists(env_file):
        logger.error(f"Archivo {env_file} no encontrado.")
        return

    with open(env_file) as f:
        lines = f.readlines()

    stripe_keys = {
        "STRIPE_SECRET_KEY": None,
        "STRIPE_WEBHOOK_SECRET": None,
        "STRIPE_PRICE_TABLE": None
    }

    for line in lines:
        for key in stripe_keys:
            if line.startswith(f"{key}="):
                stripe_keys[key] = line.split("=")[1].strip()

    # Análisis de salud del pipeline
    is_live = False
    if stripe_keys["STRIPE_SECRET_KEY"] and stripe_keys["STRIPE_SECRET_KEY"].startswith("sk_live"):
        is_live = True

    print(f"[*] Modo actual: {'🟢 LIVE' if is_live else '🟡 TEST'}")

    # Verificación de Price Table
    try:
        price_table = json.loads(stripe_keys["STRIPE_PRICE_TABLE"] or "{}")
        if "pro" in price_table and price_table["pro"].startswith("price_"):
            print("[✓] Price Table: Configurada correctamente.")
        else:
            print("[!] Price Table: Falta el ID de precio 'pro' (ej: price_123...).")
    except Exception:
        print("[X] Price Table: Error de parsing JSON.")

    if not is_live:
        print("\nPASOS PARA ACTIVAR LIVE:")
        print("1. Ve al Stripe Dashboard (Symmetric Key).")
        print("2. Crea un Product 'CORTEX Pro' ($29/mo).")
        print("3. Obtén el Price ID (price_...).")
        print(f"4. Actualiza {env_file} con las claves sk_live_... y el nuevo Price ID.")
        print("5. Configura el Webhook en Stripe apuntando a su dominio /v1/stripe/webhook.")
    else:
        print("\n[🚀] PIPELINE LIVE DETECTADA. Todo listo para facturación real.")


if __name__ == "__main__":
    check_live_status()
