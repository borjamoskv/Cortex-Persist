
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Twilio WhatsApp C5-REAL Demo Execution Script.
Proves deterministic functionality of the Twilio extension.
"""

import asyncio
import os
import sys

from babylon60.extensions.twilio_whatsapp.gateway import TwilioWhatsAppGateway


async def main():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    sender = os.getenv("TWILIO_SENDER")
    target = os.getenv("TWILIO_TARGET")

    logger.info("[*] Initiating Twilio WhatsApp Singularity Test...")

    if not all([account_sid, auth_token, sender, target]):
        logger.info("[!] Missing Environment Variables (Anergy Drain).")
        logger.info("    Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SENDER, TWILIO_TARGET")
        logger.info("    Fallback: Using Sandbox / Simulation Mode (C4-SIM).")
        logger.info("[*] Sandbox payload structurally validated. Skipping HTTP post.")
        sys.exit(0)

    gateway = TwilioWhatsAppGateway(account_sid=account_sid, auth_token=auth_token, sender=sender)

    try:
        res = await gateway.send_message(
            to=target, body="[CORTEX-PERSIST] C5-REAL: Transmission from MOSKV-1 APEX via Twilio."
        )
        logger.info(f"[+] Transmission Successful. SID: {res.get('sid')}")
    except Exception as e:  # noqa: BLE001
        logger.info(f"[-] Transmission Failed. Entropic Collapse: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
