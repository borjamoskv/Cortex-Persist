#!/usr/bin/env python3
"""
Trigger an anomaly signal in CORTEX to test the SAP Alba SSE pulse.
"""

import json
import os
import sqlite3
import sys


def main():
    db_path = os.path.expanduser("~/.cortex/cortex.db")
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
        payload = json.dumps(
            {"severity": "CRITICAL", "message": "Unauthorized transaction detected"}
        )

        # Insert a signal that will act as a trigger
        # We use event_type='sap_anomaly' as implemented in SovereignReporter
        conn.execute(
            "INSERT INTO signals (event_type, payload, source, project) VALUES (?, ?, ?, ?)",
            ("sap_anomaly", payload, "sap_alba", "SAP"),
        )

        # To ensure pragma data_version changes, just insert an edge if needed,
        # but the signal insert alone is enough to tick PRAGMA data_version in SQLite.
        conn.commit()
        conn.close()
        print("Anomaly triggered successfully! The SAP Alba UI should pulse red instantly.")

    except Exception as e:
        print(f"Failed pattern execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
