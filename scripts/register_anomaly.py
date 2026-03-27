#!/usr/bin/env python3
"""
Sovereign Script: Anomaly Registration (Signal Infiltration)
Registers high-exergy signal infiltrations (like the Hypebeast infiltration) 
into the CORTEX cryptographically verified ledger.

Ω₄ · La Ley Soberana: No se usan métricas parea marketing, sino como 
transferencia termo-informática cristalizada en el ledger.
"""

from __future__ import annotations

import sys
import asyncio
import logging
import argparse

from cortex.engine import CortexEngine

# Formatting logs to match Industrial Noir 2026 aesthetic
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | CORTEX-ANOMALY | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("cortex.anomaly")

async def inject_anomaly(vector: str, friction: float, opens: int, clicks: int, project: str = "borjamoskv_site"):
    """Injects the anomalous infiltration right into CORTEX."""
    
    # Initialize the engine
    engine = CortexEngine()
    await engine.init_db()
    
    content = f"CORTEX-ORBITAL-STRIKE: Vector {vector} breached protocol. Opens: {opens} | Clicks: {clicks} | Friction Penetration: {friction}%."
    
    meta = {
        "vector": vector,
        "friction_overcome_pct": friction,
        "metrics": {
            "opens": opens,
            "clicks": clicks
        },
        "event_type": "signal_infiltration",
        "cognitive_layer": "structural",
        "aesthetic": "Industrial Noir 2026",
        "causal_confidence": "C5-Dynamic" # Verified by telemetry
    }
    
    try:
        fact_id = await engine.store(
            content=content,
            fact_type="event",
            project=project,
            tags=["anomaly", "orbit_strike", "hypebeast", "C5-Dynamic"],
            confidence="C5-Dynamic",
            meta=meta
        )
        logger.info(f"CORTEX Ledger updated. Infiltration locked at Fact ID: {fact_id}")
        return fact_id
    finally:
        await engine.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CORTEX Anomaly Injector")
    parser.add_argument("--vector", type=str, default="editorial@hypebeast.com", help="External infiltrator vector")
    parser.add_argument("--opens", type=int, default=16, help="Number of telemetry opens")
    parser.add_argument("--clicks", type=int, default=14, help="Number of extracted clicks")
    parser.add_argument("--project", type=str, default="borjamoskv_site", help="CORTEX Project Root")
    
    args = parser.parse_args()
    
    # Calculate friction penetration ratio
    friction = 0.0
    if args.opens > 0:
        friction = round((args.clicks / args.opens) * 100, 2)

    logger.info(f"Initiating Anomaly Injection for {args.vector} into {args.project}...")
    
    try:
        fact_id = asyncio.run(inject_anomaly(args.vector, friction, args.opens, args.clicks, args.project))
        logger.info("Taint signature confirmed. Node extraction completed.")
    except Exception as e:
        logger.error(f"Failed to inject anomaly to the ledger: {e}")
        sys.exit(1)
