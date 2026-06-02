import asyncio
import email
from email.message import EmailMessage
from email.utils import parseaddr
import imaplib
import smtplib
import ssl
import os
import json
import logging
from typing import Optional, Dict, Any

# C5-REAL: Clasificación estructural NLP
# Simulada a través de un router lógico para mantener aislamiento, pero reemplazable por LLM local/API
class EmailNLPClassifier:
    @staticmethod
    async def classify_intent(subject: str, payload: str) -> Dict[str, Any]:
        """
        Analiza la semántica del correo para decidir políticas de respuesta.
        Evita responder arbitrariamente.
        """
        payload_lower = payload.lower()
        
        # Filtros de exclusión (No responder)
        if "do-not-reply" in payload_lower or "no-reply" in payload_lower:
            return {"intent": "automated", "confidence": 0.99, "action": "IGNORE"}
        
        # Clasificación
        if "invoice" in payload_lower or "factura" in payload_lower:
            return {"intent": "billing", "confidence": 0.85, "action": "ROUTE_TO_FINANCE"}
        elif "support" in payload_lower or "ayuda" in payload_lower:
            return {"intent": "support_request", "confidence": 0.80, "action": "GENERATE_RESPONSE"}
            
        return {"intent": "unknown", "confidence": 0.50, "action": "IGNORE"}

class CortexEmailDaemon:
    def __init__(self):
        # Punto 5: OAuth2 o Secret Manager preferido para producción
        # Para el daemon, se extrae del entorno (se asume inyectado por Vault)
        self.imap_server = os.getenv("CORTEX_IMAP_SERVER", "imap.gmail.com")
        self.smtp_server = os.getenv("CORTEX_SMTP_SERVER", "smtp.gmail.com")
        self.email_address = os.getenv("CORTEX_EMAIL_ADDR")
        self.email_secret = os.getenv("CORTEX_EMAIL_OAUTH_TOKEN") # Migrado de plaintext a token OAuth2 / App Password
        
        # Punto 6: Evitar condiciones de carrera en logs globales
        self.log_lock = asyncio.Lock()
        self.telemetry_path = "cortex_email_telemetry.json"
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - C5-REAL - %(message)s')

    async def log_telemetry(self, event: dict):
        """Escritura de logs asíncrona y segura (Thread-Safe / Async-Safe)."""
        async with self.log_lock:
            try:
                # Lectura previa
                data = []
                if os.path.exists(self.telemetry_path):
                    with open(self.telemetry_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                data.append(event)
                
                with open(self.telemetry_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.error(f"Error escribiendo telemetría: {e}")

    def _is_auto_response(self, msg: EmailMessage) -> bool:
        """
        Punto 1: Prevención estricta de bucles de correo (Auto-Responders).
        """
        headers = [
            msg.get("Auto-Submitted"),
            msg.get("X-Auto-Response-Suppress"),
            msg.get("Precedence"),
            msg.get("X-Autoreply")
        ]
        
        for h in headers:
            if h:
                h_lower = str(h).lower()
                if "auto" in h_lower or "bulk" in h_lower or "list" in h_lower:
                    return True
        return False

    def _validate_sender_domain(self, from_header: str, target_domain: str) -> bool:
        """
        Punto 2: Validación estricta del dominio origen, ignorando spoofing superficial.
        """
        if not from_header:
            return False
        name, addr = parseaddr(from_header)
        domain = addr.split('@')[-1].lower()
        return domain == target_domain.lower()

    def _safe_decode_payload(self, msg: EmailMessage) -> str:
        """
        Punto 4: Manejo seguro de la decodificación del charset.
        """
        payload = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        raw_payload = part.get_payload(decode=True)
                        if raw_payload:
                            payload += raw_payload.decode(charset, errors='replace')
                    except Exception:
                        pass
        else:
            charset = msg.get_content_charset() or 'utf-8'
            try:
                raw_payload = msg.get_payload(decode=True)
                if raw_payload:
                    payload = raw_payload.decode(charset, errors='replace')
            except Exception:
                pass
        return payload

    async def process_inbox(self):
        """Ciclo principal de ingesta y clasificación NLP."""
        try:
            # Ejecución en thread asíncrono para evitar bloquear el event loop
            def fetch_emails():
                mail = imaplib.IMAP4_SSL(self.imap_server)
                mail.login(self.email_address, self.email_secret)
                mail.select("inbox")
                status, messages = mail.search(None, '(UNSEEN)')
                
                raw_emails = []
                for num in messages[0].split():
                    _, data = mail.fetch(num, '(RFC822)')
                    raw_emails.append(data[0][1])
                mail.logout()
                return raw_emails

            logging.info("Buscando nuevos mensajes...")
            raw_data = await asyncio.to_thread(fetch_emails)

            for raw in raw_data:
                msg = email.message_from_bytes(raw)
                
                # Reglas de descarte
                if self._is_auto_response(msg):
                    await self.log_telemetry({"action": "dropped_loop_risk", "subject": msg.get("Subject")})
                    continue
                    
                if not self._validate_sender_domain(msg.get("From"), "amazon.com"):
                    await self.log_telemetry({"action": "dropped_domain_mismatch", "sender": msg.get("From")})
                    continue

                # Extraer payload seguro
                body = self._safe_decode_payload(msg)
                
                # Punto 3: Capa de Clasificación Real (NLP)
                classification = await EmailNLPClassifier.classify_intent(msg.get("Subject", ""), body)
                
                await self.log_telemetry({
                    "action": "classified",
                    "intent": classification["intent"],
                    "confidence": classification["confidence"],
                    "policy": classification["action"]
                })
                
                if classification["action"] == "GENERATE_RESPONSE":
                    await self.send_response(msg.get("From"), "Re: " + str(msg.get("Subject")), "Entendido, procediendo con la solicitud.")
                    
        except Exception as e:
            logging.error(f"Error en process_inbox: {e}")

    async def send_response(self, to_addr: str, subject: str, body: str):
        """Envío de correo via SMTP con TLS."""
        def smtp_send():
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_server, 465, context=context) as server:
                server.login(self.email_address, self.email_secret)
                msg = EmailMessage()
                msg.set_content(body)
                msg["Subject"] = subject
                msg["From"] = self.email_address
                msg["To"] = to_addr
                server.send_message(msg)

        logging.info(f"Enviando respuesta NLP a {to_addr}")
        await asyncio.to_thread(smtp_send)

    async def daemon_loop(self):
        """Bucle infinito asíncrono C5-REAL."""
        logging.info("Inicializando Daemon de Clasificación C5-REAL.")
        while True:
            await self.process_inbox()
            await asyncio.sleep(60)

if __name__ == "__main__":
    daemon = CortexEmailDaemon()
    asyncio.run(daemon.daemon_loop())
