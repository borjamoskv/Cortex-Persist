import base64
import logging
import sys
from email.message import EmailMessage
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Insertar el path de MAILTV-1 para reutilizar el módulo de auth
MAILTV_PATH: Path = Path.home() / ".cortex" / "mailtv" / "scripts"
if str(MAILTV_PATH) not in sys.path:
    sys.path.append(str(MAILTV_PATH))

try:
    import auth
    from googleapiclient.discovery import build
except ImportError as e:
    logger.error("Error importando dependencias de MAILTV-1: %s", e)
    sys.exit(1)

DOSSIER_PATH: Path = (
    Path(__file__).parent / "data" / "legal_dossiers" / "KUCOIN_LEGAL_NOTICE_20260223.txt"
)


def send_kucoin_dossier() -> None:
    """Envía el dossier legal formatiado a KuCoin utilizando MAILTV-1."""
    # 1. Autenticar usando credenciales de MAILTV-1
    creds = auth.authenticate()
    service = build("gmail", "v1", credentials=creds)

    # 2. Leer el dossier generado
    if not DOSSIER_PATH.exists():
        logger.error("Error: No se encuentra el dossier en %s", DOSSIER_PATH)
        return

    content: str = DOSSIER_PATH.read_text(encoding="utf-8")

    # Reemplazar el placeholder de la víctima por su ENS principal ya que no tengo las direcciones literales.
    content = content.replace(
        "[INSERTA LAS WALLETS QUE TE HACKEARON AQUÍ]", "borja.moskv.eth (Associated Wallets)"
    )

    # 3. Construir el mensaje
    message = EmailMessage()
    message.set_content(content)

    # Destinatarios de Legal/Compliance de KuCoin
    message["To"] = "legal@kucoin.com, compliance@kucoin.com, support@kucoin.com"
    message["From"] = "borjamoskv@gmail.com"
    message["Subject"] = (
        "URGENT COMPLIANCE NOTICE: Traced Stolen Funds & EIP-7702 Exploit (borja.moskv.eth)"
    )

    # 4. Codificar e inyectar
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}

    try:
        # Usamos messages().send() ejecutando directo sin pasar por drafts
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        logger.info("✅ [MAILTV-1] DISPARO CONFIRMADO. Dossier ENVIADO a Legal de KuCoin.")
        logger.info("ID del Mensaje: %s", sent_message["id"])
    except Exception as e:
        logger.error("❌ Error enviando mensaje: %s", e)


def main() -> None:
    send_kucoin_dossier()


if __name__ == "__main__":
    main()
