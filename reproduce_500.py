import os
import sys

# Ensure we can import from local cortex
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cortex.engine.membrane.sanitizer import SovereignSanitizer


def reproduce():
    # Mock the data that was sent in seed_cogito.py
    fact_type = "knowledge"
    project = "cortex"
    content = "## COGITO: Introspección Mecánica (v1.0)\n\n> 'El agente propone en probabilidad. La infraestructura dispone en matemáticas. La termodinámica cobra el peaje.'"
    source = ""
    meta = {}

    raw_engram = {
        "type": fact_type,
        "source": source,
        "topic": project,
        "content": content,
        "metadata": meta,
    }

    try:
        from cortex.engine.storage_guard import StorageGuard

        print("Testing StorageGuard.validate...")
        StorageGuard.validate(
            project=project,
            content=content,
            fact_type=fact_type,
            source=source,
            meta=meta,
        )
        print("✅ StorageGuard passed!")
    except Exception as e:
        print(f"❌ StorageGuard failed: {type(e).__name__}: {e}")

    try:
        print("\nTesting SovereignSanitizer.digest...")
        pure, log = SovereignSanitizer.digest(raw_engram)
        print("✅ Purification successful!")
        print(f"Purified content: {pure.content[:50]}...")
    except ValueError as e:
        print(f"❌ Purification failed: {e}")
    except Exception as e:
        print(f"💥 Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reproduce()
