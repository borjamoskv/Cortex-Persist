#!/usr/bin/env python3
"""
Mode: C5-REAL
Type: Emitter
Target: CORTEX LIVE / Aether Matrix SSE bus
Source: Antigravity 2.0.6
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cortex import config
from cortex.extensions.signals.bus import SignalBus

def main():
    parser = argparse.ArgumentParser(description="Emit C5-REAL")
    parser.add_argument("payload")
    parser.add_argument("--source", default="antigravity_2.0.6")
    parser.add_argument("--type", default="exergy.live.payload")

    args = parser.parse_args()

    try:
        payload_data = json.loads(args.payload)
    except json.JSONDecodeError:
        payload_data = {"content": args.payload}

    db_path = config.DB_PATH
    if not os.path.exists(db_path):
        sys.exit(f"C5-REAL-FAIL: DB not found -> {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        bus = SignalBus(conn)
        signal_id = bus.emit(event_type=args.type, payload=payload_data, source=args.source)
        sys.stdout.write(f"C5-REAL: Signal ID -> {signal_id}\n")
        sys.exit(0)
    except Exception as e:
        sys.exit(f"C5-REAL-FAIL: Emit -> {e}")

if __name__ == "__main__":
    main()
