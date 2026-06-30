import email
import imaplib
import logging
import os
import re
from typing import Optional

logger = logging.getLogger("Cortex.GmailMagicLink")


class GmailMagicLinkExtractor:
    """
    [C5-REAL] Extractor Autónomo de Autenticación.
    Bypassa la barrera Magic Link de Substack interceptando el token criptográfico
    directamente desde el servidor IMAP del Operador.
    """

    def __init__(self):
        self.email_user = os.getenv("CORTEX_EMAIL_USER")
        self.email_pass = os.getenv("CORTEX_EMAIL_APP_PASSWORD")
        self.imap_server = os.getenv("CORTEX_IMAP_SERVER", "imap.gmail.com")

    def extract_latest_magic_link(self) -> Optional[str]:
        """
        Lee el inbox, localiza el último correo de Substack de sign-in y extrae la URL.
        """
        if not self.email_user or not self.email_pass:
            logger.error(
                "Credenciales IMAP no configuradas (CORTEX_EMAIL_USER, CORTEX_EMAIL_APP_PASSWORD)"
            )
            return None

        try:
            # Conexión IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            # Buscar correos de Substack recientes
            # Criterio: De substack.com
            status, messages = mail.search(
                None, '(FROM "substack.com" SUBJECT "Sign in to Substack")'
            )
            if status != "OK":
                logger.warning("Fallo en la búsqueda IMAP.")
                return None

            msg_ids = messages[0].split()
            if not msg_ids:
                logger.warning("No se encontró ningún Magic Link en el Inbox.")
                return None

            # Coger el último (el ID más alto)
            latest_id = msg_ids[-1]
            status, msg_data = mail.fetch(latest_id, "(RFC822)")
            if status != "OK":
                logger.error("Fallo al descargar el correo.")
                return None

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extraer el cuerpo
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type in ["text/html", "text/plain"]:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")

            # Buscar la URL de login. Suele estar en href="https://<dominio>.substack.com/login/confirm_login?..."
            match = re.search(r'href="(https://[^"]+substack\.com/login/confirm_login[^"]+)"', body)
            if match:
                magic_link = match.group(1)
                logger.info("[C5-REAL] Magic Link criptográfico extraído exitosamente.")
                return magic_link

            logger.warning("No se encontró el regex del Magic Link en el cuerpo.")
            return None

        except Exception as e:  # noqa: BLE001
            logger.error(f"Fricción termodinámica en conexión IMAP: {e}")
            return None
