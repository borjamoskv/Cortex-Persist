import sys
sys.path.append("cortex-core")
import cortex_rs
from persistence import _get_ring_buffer
print(cortex_rs)
buf = cortex_rs.ZeroCopyRingBuffer("test_ring.bin", 1000)
print(buf)
print("Enqueuing...")
buf.enqueue(b"agent1", b"payload")
print("Done.")
