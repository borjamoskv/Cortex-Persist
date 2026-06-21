import struct
import time
from collections import deque
import numpy as np

class AzkartuReplayBuffer:
    def __init__(self, capacity=1000000):
        self.buffer = deque(maxlen=capacity)
        # Lectura directa del ledger AOF generado por Rust
        self.ledger_path = "/var/cortex/azkartu_ledger.aof"
        self.cursor = 0

    def sync_from_ledger(self):
        try:
            with open(self.ledger_path, "rb") as f:
                f.seek(self.cursor)
                while True:
                    # Asumiendo un struct C-repr binario (State, Policy, Reward)
                    chunk = f.read(1032) # Tamaño precalculado del byte-frame
                    if not chunk or len(chunk) < 1032:
                        break
                    
                    # Desempaquetar bytes directamente a numpy/tuplas
                    state, pi, z = self._unpack_frame(chunk)
                    self.buffer.append((state, pi, z))
                    self.cursor += 1032
        except FileNotFoundError:
            pass

    def _unpack_frame(self, chunk):
        # Placeholder for C-struct unpacking
        # Struct needs to be perfectly aligned with Rust
        state = np.zeros((8, 8))
        pi = np.zeros(64)
        z = 0.0
        return state, pi, z
