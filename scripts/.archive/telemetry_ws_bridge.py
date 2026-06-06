#!/usr/bin/env python3
"""
CORTEX Telemetry Daemon (C5-REAL)
Streams Zero-GIL swarm metrics to the EXERGIA-Ω Industrial Noir dashboard.

Self-contained: no CORTEX engine imports required.
Simulation mode: "Consejo de Sabios" - 1000-agent breathing synchronization.
"""

import asyncio
import json
import logging
import math
import random
import time

try:
    import websockets
except ImportError:
    import logging

    logging.warning("Instalando dependencia websockets...")
    import subprocess

    subprocess.run(["pip", "install", "websockets"], check=True)
    import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - CORTEX-WS - %(message)s")


def _audit_payload_inline(payload: dict, event_id: str) -> list[dict]:
    """Minimal JIS audit - checks signature presence (SOC2/C5 gate)."""
    violations = []
    if "signature" not in payload:
        violations.append(
            {
                "rule": "JIS-001-SIGNATURE",
                "severity": "CRITICAL",
                "event_id": event_id,
                "detail": "Missing cryptographic signature on telemetry payload",
            }
        )

    metrics = payload.get("metrics", {})
    cortisol = metrics.get("cortisol_level", 0.0)
    if cortisol > 0.8:
        violations.append(
            {
                "rule": "THERMODYNAMIC_STRESS_CRITICAL",
                "severity": "HIGH",
                "event_id": event_id,
                "detail": f"Systemic cortisol ({cortisol:.2f}) exceeded 0.8 threshold. High risk of entropic decay.",
            }
        )

    return violations


async def telemetry_loop(websocket):
    logging.info("C5-REAL: Frontend Dashboard conectado al flujo de telemetría.")
    try:
        base_throughput = 390534.73
        tick_count = 0
        while True:
            tick_count += 1
            # Simulación "Consejo de Sabios" (Deep Breathing / Synchronization)
            phase = tick_count * 0.05
            breathing = math.sin(phase)
            sync_pulse = math.cos(phase * 0.5)

            cortisol_val = 0.3 + (breathing * 0.2) + random.uniform(0.01, 0.05)
            exergy_val = 0.02 + (sync_pulse * 0.015) + random.uniform(0.001, 0.005)
            throughput = base_throughput + (breathing * 150000)

            metrics = {
                "active_nodes": 1000,
                "active_tasks": int(1000 + random.uniform(-50, 50)),
                "throughput_agents_sec": round(max(10000, throughput), 2),
                "gil_friction_us": 0.0,
                "ring_buffer_utilization": round(random.uniform(0.1, 0.5), 2),
                "exergy_consumption_j": round(exergy_val, 4),
                "cortisol_level": round(cortisol_val, 3),
            }
            payload = {
                "timestamp": time.monotonic(),
                "swarm_state": "LEGION-1K // CONSEJO_DE_SABIOS",
                "actor_id": "cortex-telemetry-daemon",
                "signature": "0xCRYPTO_MOCK_SIGNATURE",
                "metrics": metrics,
            }

            # Simulate a C5 signature violation every 50 ticks
            if tick_count % 50 == 0:
                payload.pop("signature")

            # Simulate a Cortisol spike every 200 ticks (10s) to trigger THERMODYNAMIC_STRESS_CRITICAL
            if tick_count % 200 < 10:
                payload["metrics"]["cortisol_level"] = 0.85 + random.uniform(0.0, 0.1)

            violations = _audit_payload_inline(payload, event_id=f"tick_{tick_count}")
            payload["jis_violations"] = violations

            # Periodic log (every 100 ticks = 5s at 20Hz)
            if tick_count % 100 == 0:
                logging.info(
                    f"C5-REAL: tick={tick_count} cortisol={cortisol_val:.3f} "
                    f"exergy={exergy_val:.4f} violations={len(violations)}"
                )

            await websocket.send(json.dumps(payload))
            await asyncio.sleep(0.05)  # 20Hz Tick Rate para estética fluida
    except websockets.exceptions.ConnectionClosed:
        logging.info("C5-REAL: Conexión terminada con el Dashboard.")


async def main():
    server = await websockets.serve(telemetry_loop, "127.0.0.1", 8081)
    logging.info("===================================================")
    logging.info(" ⚡ CORTEX SOVEREIGN TELEMETRY DAEMON INICIADO")
    logging.info(" 🔌 WebSocket Bridge: ws://127.0.0.1:8081")
    logging.info(" 📡 Objetivo: EXERGIA-Ω Dashboard")
    logging.info(" 🫁 Modo: CONSEJO_DE_SABIOS (1000 agentes)")
    logging.info("===================================================")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
