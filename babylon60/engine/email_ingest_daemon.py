# [C5-REAL] Exergy-Maximized
import asyncio
import email
import email.policy
import imaplib
import logging
import os

from babylon60.audit.ledger import EnterpriseAuditLedger
from babylon60.engine.zipf_exergy_extractor import ZipfExergyExtractor

logger = logging.getLogger(__name__)

class EmailIngestDaemon:
    """
    [C5-REAL] Daemon residente de ingesta IMAP.
    Vigila el buzón de correo y colapsa correos electrónicos en nodos causales
    (LedgerFacts) mediante validación criptográfica en el Master Ledger.
    """

    def __init__(self, ledger: EnterpriseAuditLedger, scan_interval: int = 60):
        self.ledger = ledger
        self.interval = scan_interval
        self._running = False
        self._task = None

        self.imap_server = os.environ.get("CORTEX_IMAP_SERVER")
        self.imap_user = os.environ.get("CORTEX_IMAP_USER")
        self.imap_pass = os.environ.get("CORTEX_IMAP_PASS")
        self.tenant_id = os.environ.get("CORTEX_TENANT_ID", "CORTEX-GLOBAL")

    def _sync_fetch_emails(self):
        """Bloqueo síncrono encapsulado en thread para interactuar con IMAP."""
        if not self.imap_server or not self.imap_user or not self.imap_pass:
            logger.warning("[EmailIngestDaemon] Credenciales IMAP no configuradas en el entorno.")
            return []

        messages = []
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.imap_user, self.imap_pass)
            mail.select("inbox")

            status, data = mail.search(None, "UNSEEN")
            if status != "OK" or not data[0]:
                mail.logout()
                return []

            for num in data[0].split():
                status, msg_data = mail.fetch(num, "(RFC822)")
                if status == "OK" and msg_data:
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1], policy=email.policy.default)
                            subject = msg.get("subject", "No Subject")
                            sender = msg.get("from", "Unknown")
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    ctype = part.get_content_type()
                                    if ctype == "text/plain":
                                        body = part.get_payload(decode=True)
                                        if isinstance(body, bytes):
                                            body = body.decode(errors="ignore")
                                        break
                            else:
                                body = msg.get_payload(decode=True)
                                if isinstance(body, bytes):
                                    body = body.decode(errors="ignore")

                            messages.append({
                                "subject": str(subject),
                                "sender": str(sender),
                                "body": str(body)
                            })
            mail.logout()
        except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
            logger.error(f"[EmailIngestDaemon] Fallo en fetch IMAP: {e}")
        return messages

    async def _daemon_loop(self):
        self._running = True
        logger.info("[EmailIngestDaemon] Inicializado. Vigilancia IMAP activa.")
        while self._running:
            try:
                # 1. Ejecutar lectura en hilo para no bloquear el event loop (C5-REAL anti-entropía)
                emails = await asyncio.to_thread(self._sync_fetch_emails)

                # 2. Enrutamiento Causal
                for mail in emails:
                    sender = mail["sender"]
                    subject = mail["subject"]
                    body = mail["body"]
                    
                    # Vector 1: Zero-Trust CLI (Sovereign Operator)
                    if "borjabilbo84@gmail.com" in sender or "info@cortexpersist.com" in sender:
                        logger.info(f"[EmailIngestDaemon] Ingestando Directiva de Autoridad {sender}: {subject}")
                        await self.ledger.log_action(
                            tenant_id=self.tenant_id,
                            actor_role="SOVEREIGN_OPERATOR",
                            actor_id=sender,
                            action="IMAP_DIRECTIVE",
                            resource=subject,
                            status="SUCCESS",
                            state_diff=body,
                            is_code=False
                        )
                    # Vector 2: Zipf Exergy Extractor (External Agents)
                    else:
                        logger.info(f"[EmailIngestDaemon] Evaluando entropía de tercero {sender}: {subject}")
                        # Extraer Primitivas (Fase 1)
                        nodes = ZipfExergyExtractor.extract_exergy_primitives(body, max_nodes=50)
                        # Evaluar Limerencia (Fase 2)
                        evaluation = ZipfExergyExtractor.evaluate_epistemic_limerence(nodes)
                        
                        action_type = "IMAP_REJECTED_ANERGY"
                        if evaluation["ExergyConfidence"] == "C5-REAL":
                            action_type = "IMAP_BOUNTY_LEAD"
                        
                        await self.ledger.log_action(
                            tenant_id=self.tenant_id,
                            actor_role="EXTERNAL_AGENT",
                            actor_id=sender,
                            action=action_type,
                            resource=subject,
                            status="SUCCESS",
                            state_diff=f"{evaluation}\n\nORIGINAL_BODY:\n{body}",
                            is_code=False
                        )

            except asyncio.CancelledError:
                break
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
                logger.error(f"[EmailIngestDaemon] Fallo en ciclo de ingesta: {e}")

            if self._running:
                await asyncio.sleep(self.interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daemon_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as exc:  # P0-PURGED
                logger.warning("Suppressed exception: %s", exc)
            logger.info("[EmailIngestDaemon] Terminado. Conexión IMAP cerrada.")
