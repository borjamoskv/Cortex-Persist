import os
import sys
from cortex.guards.duress_guard import DuressGuard

def test_crash(test_name, payload):
    print(f"\n--- Testing: {test_name} ---")
    os.environ["GEMINI_API_KEY"] = payload
    try:
        DuressGuard.execute_apoptosis()
        print(f"SUCCESS: No crash for {test_name}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_crash("Non-ASCII string (UTF-16/32 in memory)", "cortex_key_ñ_🚀")
