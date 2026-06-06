# [C5-REAL] Exergy-Maximized
import time

t0 = time.monotonic()
from cortex.sovereign.bridge import SovereignBridge

bridge = SovereignBridge()
print(f"Elapsed: {(time.monotonic() - t0) * 1000:.2f} ms")
