#!/usr/bin/env python3
"""
Aether to OSC Bridge (CORTEX LIVE ↔ Visuals/Audio)
Reality Level: C5-REAL

Listens to the CORTEX Aether Matrix (SSE) and converts deterministic exergy events
into Open Sound Control (OSC) packets for Ableton, TouchDesigner, or MaxMSP.
"""

import json
import logging
import socket
import sys
import urllib.error
import urllib.request

# Config
SSE_URL = "http://127.0.0.1:8000/api/v1/events/stream"
OSC_IP = "127.0.0.1"
OSC_PORT = 8001  # Port TouchDesigner / Ableton listens to

logger = logging.getLogger("AetherOSC")
setup_cortex_logging()


def create_osc_message(address: str, arg: str) -> bytes:
    """Builds a raw OSC packet without external dependencies."""

    def _pad(s: bytes) -> bytes:
        return s + (b"\x00" * (4 - (len(s) % 4)))

    addr_bytes = _pad(address.encode("utf-8") + b"\x00")
    tags = _pad(b",s\x00")
    arg_bytes = _pad(arg.encode("utf-8") + b"\x00")

    return addr_bytes + tags + arg_bytes


def main():
    logger.info("🌌 Aether OSC Bridge Started [C5-REAL]")
    logger.info(f"📡 Listening: {SSE_URL}")
    logger.info(f"🎯 Output (OSC): {OSC_IP}:{OSC_PORT}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        req = urllib.request.Request(SSE_URL, headers={"Accept": "text/event-stream"})
        with urllib.request.urlopen(req) as response:
            current_event = None

            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue

                if line.startswith("event:"):
                    current_event = line.split("event: ")[1]
                elif line.startswith("data:") and current_event == "exergy.live.payload":
                    data_str = line[5:].strip()
                    try:
                        data_json = json.loads(data_str)
                        payload = data_json.get("payload", {})

                        # Map JSON to OSC
                        osc_address = f"/cortex/exergy/{payload.get('action', 'raw')}"
                        osc_arg = json.dumps(payload)

                        # Fire UDP Packet
                        sock.sendto(create_osc_message(osc_address, osc_arg), (OSC_IP, OSC_PORT))

                        logger.info(f"⚡ [OSC BLASTER] -> {osc_address}")

                    except json.JSONDecodeError:
                        pass
                    current_event = None

    except urllib.error.URLError as e:
        logger.error(
            f"FATAL: Cannot connect to Aether Matrix ({SSE_URL}). Is CORTEX running? Error: {e}"
        )
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nBridge closed. Entropy preserved.")
        sys.exit(0)


if __name__ == "__main__":
    main()
