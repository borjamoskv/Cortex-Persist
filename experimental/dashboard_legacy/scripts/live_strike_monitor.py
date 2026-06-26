#!/usr/bin/env python3
import time
import sqlite3
from pathlib import Path

# Common Cortex Colors
C = {
    "B": "\033[38;2;43;59;229m",
    "G": "\033[38;2;0;255;136m",
    "V": "\033[38;2;102;0;255m",
    "W": "\033[97m",
    "X": "\033[0m",
}

DB_PATH = Path.home() / ".cortex/cortex_native_ledger.db"

def monitor():
    print(f"\n{C['B']}∴ Ouroboros Strike Monitor v1.0{C['X']}")
    print(f"{C['W']}Watching: {DB_PATH}{C['X']}\n")
    
    last_count = 0
    
    while True:
        try:
            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Summary stats
            cursor.execute("SELECT COUNT(*) FROM bounties")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bounties WHERE status='exploited'")
            exploited = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bounties WHERE status='archived'")
            cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bounties WHERE status='found' AND exergy >= 5.0")
            vip_pending = cursor.fetchone()[0]

            if total != last_count:
                print(f"  {C['W']}Status Cycle: Total={total} | {C['G']}Exploited={exploited}{C['X']} | {C['V']}VIP_Pending={vip_pending}{C['X']}")
                last_count = total
                
                # Fetch last 3 successes
                cursor.execute("SELECT title, exergy, updated_at FROM bounties WHERE status='exploited' ORDER BY updated_at DESC LIMIT 3")
                successes = cursor.fetchall()
                for s in successes:
                    print(f"    {C['G']}✔ SUCCESS:{C['X']} {s[0]} (Exergy: {s[1]}) at {s[2]}")

            conn.close()
        except Exception as e:
            print(f"  [!] Monitor Error: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    monitor()
