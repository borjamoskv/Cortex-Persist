import logging
import sqlite3

from cortex.engine import CortexEngine

logging.basicConfig(level=logging.INFO)
engine = CortexEngine()
try:
    res = engine.store_sync(project="debug", content="debug_fact")
    print(f"\n[DEBUG] res: {res}")
    print(f"[DEBUG] type(res): {type(res)}")
except (ValueError, RuntimeError, sqlite3.Error) as e:
    print(f"[ERROR] {e}")
finally:
    engine.close_sync()
