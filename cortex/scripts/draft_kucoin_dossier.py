import base64
import os
import sys
from email.message import EmailMessage
from pathlib import Path

# Insertar el path de MAILTV-1 para reutilizar el módulo de auth
mailtv_path = os.path.expanduser("~/.cortex/mailtv/scripts")
if mailtv_path not in sys.path:
    sys.path.append(mailtv_path)

try:
    import auth
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"Error importando dependencias de MAILTV-1: {e}")
    sys.exit(1)


def create_kucoin_draft():
    # 1. Autenticar usando credenciales de MAILTV-1
    creds = auth.authenticate()
    service = build("gmail", "v1", credentials=creds)

    # 2. Leer el dossier generado
    dossier_dir = Path(__file__).parent / "data" / "legal_dossiers"
    dossier_path = str(dossier_dir / "KUCOIN_LEGAL_NOTICE_20260223.txt")
    if not os.path.exists(dossier_path):
        print(f"Error: No se encuentra el dossier en {dossier_path}")
        return

    with open(dossier_path, encoding="utf-8") as f:
        content = f.read()

    # 3. Construir el mensaje
    message = EmailMessage()
    message.set_content(content)

    # Destinatarios de Legal/Compliance de KuCoin
    message["To"] = "legal@kucoin.com, compliance@kucoin.com"
    message["From"] = "borjamoskv@gmail.com"  # Asumiendo la cuenta principal usada
    message["Subject"] = "URGENT COMPLIANCE NOTICE: Traced Stolen Funds & EIP-7702 Exploit"

    # 4. Codificar e inyectar en Drafts
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"message": {"raw": encoded_message}}

    try:
        draft = service.users().drafts().create(userId="me", body=create_message).execute()
        print("✅ [MAILTV-1] Dossier inyectado en Borradores SOBERANAMENTE.")
        print(f"ID del Borrador: {draft['id']}")
        print("Abre tu Gmail -> Borradores. Revisa el contenido y dale al botón de Enviar.")
    except Exception as e:
        print(f"❌ Error creando borrador: {e}")


if __name__ == "__main__":
    create_kucoin_draft()
