import time

t0 = time.time()
from cortex.sovereign.bridge import SovereignBridge

bridge = SovereignBridge()
print(f"Elapsed: {(time.time() - t0) * 1000:.2f} ms")
