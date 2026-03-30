import os
import sys
import time

import requests

# Configuración CORTEX Sovereign SMS
API_KEY = os.environ.get("5SIM_API_KEY", "TU_API_KEY_AQUI")
COUNTRY = "england" # Usualmente números UK, US o ES son más estables para WA

def get_whatsapp_number():
    if API_KEY == "TU_API_KEY_AQUI":
        print("[ERROR] No se detectó 5SIM_API_KEY. Obtén una en 5sim.net, recarga 1$ y añádela como variable de entorno o modifícala aquí.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }

    print(f"[CORTEX] Solicitando número virtual soberano ({COUNTRY}) para WhatsApp...")
    url = f"https://5sim.net/v1/user/buy/activation/{COUNTRY}/any/whatsapp"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        print(f"[ERROR FATAL] La pasarela 5Sim rechazó la solicitud: {res.text}")
        print("Asegúrate de tener saldo (cuesta ~$0.15 USD).")
        sys.exit(1)

    data = res.json()
    phone = data.get('phone')
    order_id = data.get('id')

    print("="*50)
    print(f"[X] IDENTIDAD VIRTUAL ADQUIRIDA: {phone}")
    print("="*50)
    print(">> Introduce este número en tu app de WhatsApp Business clonada o dispositivo secundario.")
    print(">> Pide la verificación por SMS.")
    print("\n[CORTEX] Interceptando código SMS (polling activo - timeout 15 min)...")

    while True:
        time.sleep(10)
        chk = requests.get(f"https://5sim.net/v1/user/check/{order_id}", headers=headers)
        if chk.status_code == 200:
            chk_data = chk.json()
            if chk_data.get('status') == 'FINISHED' or len(chk_data.get('sms', [])) > 0:
                code = chk_data['sms'][0]['code']
                print("\n" + "="*50)
                print(f"[CORTEX] CÓDIGO WHATSAPP EXTRAÍDO: {code}")
                print("="*50 + "\n")

                # Cerrar orden para liberar saldo retenido
                requests.get(f"https://5sim.net/v1/user/finish/{order_id}", headers=headers)
                print("[+] Identidad verificada. Orden cerrada. Motor Sovereign listo.")
                break
            elif chk_data.get('status') == 'TIMEOUT' or chk_data.get('status') == 'BANNED':
                print("\n[-] El número ha caducado o está baneado por Facebook. El saldo ha sido reembolsado.")
                print(">> Vuelve a ejecutar el script para obtener uno nuevo.")
                break
        sys.stdout.write('.')
        sys.stdout.flush()

if __name__ == "__main__":
    get_whatsapp_number()
