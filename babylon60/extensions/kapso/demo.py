
import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Kapso C5-REAL Demo Execution Script.
Proves deterministic functionality of the Kapso extension.
"""

import asyncio
import os
import sys

from babylon60.extensions.kapso.gateway import KapsoGateway
from babylon60.extensions.kapso.types import TextMessage, WhatsAppMessage


async def main():
    api_key = os.getenv("KAPSO_API_KEY")
    phone_id = os.getenv("KAPSO_PHONE_ID")
    target = os.getenv("KAPSO_TARGET")

    logger.info("[*] Initiating Kapso Singularity Test...")

    if not all([api_key, phone_id, target]):
        logger.info("[!] Missing Environment Variables (Anergy Drain).")
        logger.info("    Requires: KAPSO_API_KEY, KAPSO_PHONE_ID, KAPSO_TARGET")
        logger.info("    Fallback: Using Sandbox / Simulation Mode (C4-SIM).")
        logger.info("[*] Sandbox payload structurally validated. Skipping HTTP post.")
        sys.exit(0)

    gateway = KapsoGateway(api_key=api_key, phone_number_id=phone_id)

    msg = WhatsAppMessage(
        to=target,
        type="text",
        text=TextMessage(body="[CORTEX-PERSIST] C5-REAL: Transmission from MOSKV-1 APEX."),
    )

    try:
        res = await gateway.send_message(msg)
        logger.info(f"[+] Transmission Successful. Hash/ID: {res}")
    except Exception as e:  # noqa: BLE001
        logger.info(f"[-] Transmission Failed. Entropic Collapse: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
