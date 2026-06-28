# [C5-REAL] Exergy-Maximized
"""email.py

Servicio de transporte de Email C5-REAL (Mailgun / SendGrid).
Integra EgressGuard y firma los envíos en el Ledger antes de despachar
a la red pública para asegurar confinamiento termodinámico.
"""

import logging
import os

import httpx

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.guards.egress_guard import EgressGuard

logger = logging.getLogger("cortex.services.email")


class CortexEmailTransport:
    def __init__(self, ledger: EnterpriseAuditLedger, tenant_domains: list[str] | None = None):
        self.ledger = ledger
        self.guard = EgressGuard(tenant_domains=tenant_domains)
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY")
        self.mailgun_key = os.getenv("MAILGUN_API_KEY")
        self.mailgun_domain = os.getenv("MAILGUN_DOMAIN")

        if not self.sendgrid_key and not (self.mailgun_key and self.mailgun_domain):
            logger.warning("No API keys found for Email Transport. Will operate in dry-run mode.")

    async def _dispatch_sendgrid(self, recipient: str, subject: str, body: str) -> bool:
        if not self.sendgrid_key:
            return False

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.sendgrid_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "personalizations": [{"to": [{"email": recipient}]}],
            "from": {"email": os.getenv("CORTEX_FROM_EMAIL", "cortex@legion.local")},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=5.0)
            return resp.status_code in (200, 202)

    async def _dispatch_mailgun(self, recipient: str, subject: str, body: str) -> bool:
        if not self.mailgun_key or not self.mailgun_domain:
            return False

        url = f"https://api.mailgun.net/v3/{self.mailgun_domain}/messages"
        auth = ("api", self.mailgun_key)
        data = {
            "from": os.getenv("CORTEX_FROM_EMAIL", f"Cortex <cortex@{self.mailgun_domain}>"),
            "to": [recipient],
            "subject": subject,
            "text": body,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, auth=auth, data=data, timeout=5.0)
            return resp.status_code == 200

    async def send_email(
        self, agent_id: str, recipient: str, subject: str, body: str, tenant_id: str = "default"
    ) -> bool:
        """
        Envía un correo asíncrono aplicando EgressGuard y Ledger Logging.
        """
        # 1. EgressGuard Authorization (SAGA-1)
        auth = self.guard.authorize_email(agent_id, recipient, body)
        if not auth.authorized:
            logger.error(
                "CortexEmailTransport: Dispatch rejected for agent %s. Reason: %s",
                agent_id,
                auth.reason,
            )
            return False

        # 2. Ledger Commitment (SAGA-5)
        # Commit to the tamper-evident ledger BEFORE external side-effects
        await self.ledger.log_action(
            tenant_id=tenant_id,
            actor_role="agent",
            actor_id=agent_id,
            action="egress.email.send",
            resource=recipient,
            status="authorized",
        )

        # 3. Network Dispatch
        if self.sendgrid_key:
            success = await self._dispatch_sendgrid(recipient, subject, body)
        elif self.mailgun_key and self.mailgun_domain:
            success = await self._dispatch_mailgun(recipient, subject, body)
        else:
            # Dry-run
            logger.info("[DRY-RUN] Enviando email a %s (Subject: %s)", recipient, subject)
            success = True

        return success


# Mantener retrocompatibilidad para scripts sincrónicos antiguos (deprecated)
def send_reengagement_email(email: str, cluster: str) -> bool:
    """
    Mock implementation of email service (Deprecated).
    Use CortexEmailTransport.send_email instead for C5-REAL mode.
    """
    logger.info("Enviando email de re-engagement a %s (Cluster: %s) [DEPRECATED]", email, cluster)
    return True
