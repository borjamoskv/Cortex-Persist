"""RealMail — Manifold de Email Real para agentes MOSKV."""

from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import os
import re
import secrets
import string

import httpx

logger = logging.getLogger(__name__)

_IMAP_SERVERS: dict[str, str] = {
    "gmail.com": "imap.gmail.com",
    "outlook.com": "outlook.office365.com",
    "hotmail.com": "outlook.office365.com",
    "live.com": "outlook.office365.com",
}
_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"
_PASSWORD_LENGTH = 16
_MAILTV_TIMEOUT = 30


def _imap_server_for(domain: str) -> str:
    """Resuelve el servidor IMAP para un dominio dado."""
    for key, server in _IMAP_SERVERS.items():
        if key in domain:
            return server
    return f"imap.{domain}"


def _extract_body(msg: email.message.Message) -> str:
    """Extrae el cuerpo en texto plano de un mensaje."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="ignore")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="ignore") if payload else ""


class RealMail:
    """Manifold de Email Real para agentes MOSKV."""

    def __init__(self, provider: str = "subaddress", domain: str = "") -> None:
        self.provider = provider
        self.domain = domain
        self.api_key: str | None = os.getenv("REAL_MAIL_API_KEY")
        self.base_email: str | None = os.getenv("REAL_MAIL_BASE")
        # Tier-1 (FLAG-002): Sin fallback hardcoded. Env var obligatoria.
        self.default_password: str | None = os.getenv("REAL_MAIL_DEFAULT_PASSWORD")
        if not self.default_password and provider == "subaddress":
            logger.warning("⚠️ REAL_MAIL_DEFAULT_PASSWORD no definida. El registro de agentes puede fallar.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_password() -> str:
        """Genera una contraseña criptográficamente robusta."""
        return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(_PASSWORD_LENGTH))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_email_for_agent(self, agent_name: str) -> dict[str, str]:
        """Genera o registra un email real para el agente.

        Retorna ``{"email": "...", "password": "..."}``.
        """
        clean_name = agent_name.lower().replace(" ", "-").replace(".", "")
        password = self._generate_password()

        if self.provider == "subaddress":
            if not self.base_email or "@" not in self.base_email:
                raise ValueError("REAL_MAIL_BASE debe ser un email válido para sub-addressing")
            if not self.default_password:
                raise ValueError("REAL_MAIL_DEFAULT_PASSWORD es requerida para el provider 'subaddress'")
            user, domain = self.base_email.split("@", 1)
            return {"email": f"{user}+{clean_name}@{domain}", "password": self.default_password}

        if self.provider == "addy":
            return await self._register_addy_alias(clean_name, agent_name, password)

        return {"email": f"{clean_name}@{self.domain}", "password": password}

    async def check_verification_code(
        self,
        email_address: str,
        password: str | None = None,
        search_query: str = "Moltbook",
    ) -> str | None:
        """Busca el código de verificación (6 dígitos) en el buzón real.

        Prioriza MAILTV-1 para Gmail; hace fallback a IMAP genérico.
        """
        logger.info("🔍 Buscando verificación para %s...", email_address)

        if "gmail.com" in email_address.lower():
            code = await self._check_via_mailtv(email_address, search_query)
            if code:
                return code

        if password:
            return await self._check_via_imap(email_address, password, search_query)

        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _register_addy_alias(
        self, clean_name: str, agent_name: str, password: str
    ) -> dict[str, str]:
        """Registra un alias en Addy.io y hace fallback a subaddress si falla."""
        if not self.api_key:
            raise ValueError("REAL_MAIL_API_KEY requerido para Addy.io")

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://app.addy.io/api/v1/aliases",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "domain": self.domain,
                    "description": f"Agent: {agent_name}",
                    "format": "local_part",
                    "local_part": clean_name,
                },
            )
            if resp.status_code in (200, 201):
                return {"email": resp.json()["data"]["email"], "password": password}

            logger.error("Addy.io error %s: %s", resp.status_code, resp.text)
            return await self.get_email_for_agent(agent_name)

    async def _check_via_mailtv(self, email_address: str, search_query: str) -> str | None:
        """Consulta MAILTV-1 (Gmail OAuth2) para obtener el código."""
        try:
            token_path = os.path.expanduser("~/.cortex/mailtv/token.json")
            if not os.path.exists(token_path):
                return None

            logger.info("📡 Consultando MAILTV-1 Manifold...")
            script_path = os.path.expanduser("~/.cortex/mailtv/scripts/list_emails.py")
            cmd = ["python3", script_path, "--query", f"to:{email_address} {search_query}"]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=_MAILTV_TIMEOUT
                )
            except TimeoutError:
                proc.kill()
                logger.warning("⚠️ MAILTV-1 timeout tras %ss", _MAILTV_TIMEOUT)
                return None

            if proc.returncode != 0:
                logger.warning("⚠️ Script MAILTV-1 falló: %s", stderr.decode(errors="replace"))
                return None

            match = re.search(r"(\d{6})", stdout.decode(errors="replace"))
            return match.group(1) if match else None

        except OSError as exc:
            logger.warning("⚠️ Fallo en puente MAILTV-1: %s", exc)
            return None

    async def _check_via_imap(
        self, email_address: str, password: str, search_query: str
    ) -> str | None:
        """Consulta IMAP genérico en un thread para no bloquear el event loop."""
        domain = email_address.split("@")[-1]
        server = _imap_server_for(domain)
        logger.info("🔐 Conectando a %s via IMAP...", server)

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None, self._imap_fetch_code, server, email_address, password, search_query
            )
        except OSError as exc:
            logger.error("❌ Error IMAP: %s", exc)
            return None

    @staticmethod
    def _imap_fetch_code(
        server: str, email_address: str, password: str, search_query: str
    ) -> str | None:
        """Bloque sincrónico de IMAP — se ejecuta en un thread separado."""
        try:
            mail = imaplib.IMAP4_SSL(server)
            mail.login(email_address, password)
            mail.select("inbox")

            status, messages = mail.search(None, f'(UNSEEN TEXT "{search_query}")')
            if status != "OK" or not messages[0]:
                mail.logout()
                return None

            for num in messages[0].split()[::-1]:
                _, data = mail.fetch(num, "(RFC822)")
                raw = data[0][1]
                msg = email.message_from_bytes(raw)
                body = _extract_body(msg)
                match = re.search(r"(\d{6})", body)
                if match:
                    mail.logout()
                    return match.group(1)

            mail.logout()
        except imaplib.IMAP4.error as exc:
            logger.error("❌ IMAP protocol error: %s", exc)
        return None
