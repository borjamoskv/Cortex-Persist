from cortex.engine import CortexEngine
import logging

logging.basicConfig(level=logging.INFO)
engine = CortexEngine()
try:
    res = engine.store_sync(project="debug", content="debug_fact")
    print(f"\n[DEBUG] res: {res}")
    print(f"[DEBUG] type(res): {type(res)}")
except Exception as e:
    print(f"[ERROR] {e}")
finally:
    engine.close_sync()
