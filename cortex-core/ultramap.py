import os
import mmap
import time
import struct
import hashlib
import logging
import weakref
import atexit

DB_PATH = os.getenv(
    "CORTEX_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cortex_memory_vsa.db"),
)

logger = logging.getLogger("cortex.ultramap")

class EntropyDeath(Exception):
    pass

class UltramapSubstrate:
    """
    ULTRAMAP-Ω: Sovereign Spatial Matrix for the K-0 Swarm.
    C5-REAL Lock-Free Topological Substrate.
    
    Memory Layout per Node (96 bytes):
      [0:24]  : X, Y, Z coordinates (3x double)
      [24:88] : Target Hash (64 bytes string)
      [88:96] : Entropy Gradient (double)
    """

    def __init__(self, capacity=10000):
        self.capacity = capacity
        self.node_size = 96
        self.tensor_size = self.capacity * self.node_size
        self.bin_path = os.path.join(os.path.dirname(DB_PATH), "ultramap.bin")

        if not os.path.exists(self.bin_path) or os.path.getsize(self.bin_path) < self.tensor_size:
            os.makedirs(os.path.dirname(self.bin_path), exist_ok=True)
            with open(self.bin_path, "wb") as f:
                f.write(b"\x00" * self.tensor_size)

        self._f = open(self.bin_path, "r+b")
        self._mmap = mmap.mmap(self._f.fileno(), self.tensor_size)
        self._buffer = memoryview(self._mmap)
        
        self._finalizer = weakref.finalize(self, self._safe_close, self._mmap, self._f)
        atexit.register(self.close)
        
        logger.info(f"ULTRAMAP-Ω Initialized. Capacity: {self.capacity} agents. O(1) Memory Active.")

    @staticmethod
    def _safe_close(mmap_obj, f_obj):
        try:
            if mmap_obj:
                mmap_obj.close()
            if f_obj:
                f_obj.close()
        except Exception:
            pass

    def close(self):
        if hasattr(self, "_finalizer") and self._finalizer.alive:
            self._finalizer()

    def update_agent_position(self, agent_idx: int, x: float, y: float, z: float, target: str, entropy: float):
        """Updates the topological coordinates of a swarm agent."""
        if not (0 <= agent_idx < self.capacity):
            return False
            
        offset = agent_idx * self.node_size
        
        # We pack x, y, z first, then target_hash, then entropy
        # Let's fix the layout mapping:
        # 0-8: X
        # 8-16: Y
        # 16-24: Z
        # 24-88: Target Hash
        # 88-96: Entropy Gradient
        
        struct.pack_into("ddd", self._buffer, offset, x, y, z)
        target_bytes = target.encode('utf-8')[:64].ljust(64, b"\x00")
        self._buffer[offset + 24 : offset + 88] = target_bytes
        struct.pack_into("d", self._buffer, offset + 88, entropy)
        
        return True

    def calculate_exergy_distance(self, agent_idx: int, target_hash: str) -> float:
        """
        O(1) calculation of thermodynamic distance to target.
        Returns the Joules required to traverse the topology.
        """
        if not (0 <= agent_idx < self.capacity):
            raise EntropyDeath("Agent Index Out of Bounds")
            
        offset = agent_idx * self.node_size
        x, y, z = struct.unpack_from("ddd", self._buffer, offset)
        current_entropy = struct.unpack_from("d", self._buffer, offset + 88)[0]
        
        # Target hash defines a deterministic point in space
        target_int = int(hashlib.sha256(target_hash.encode()).hexdigest()[:16], 16)
        tx = (target_int % 1000) / 10.0
        ty = ((target_int >> 4) % 1000) / 10.0
        tz = ((target_int >> 8) % 1000) / 10.0
        
        distance = ((tx - x)**2 + (ty - y)**2 + (tz - z)**2)**0.5
        
        # Joules = Distance * (1 / (Current Entropy + 0.01))
        # High entropy areas require less exergy to exploit
        joules = distance * (1.0 / (current_entropy + 0.001))
        return joules
        
    def get_agent_state(self, agent_idx: int) -> dict:
        if not (0 <= agent_idx < self.capacity):
            return {}
            
        offset = agent_idx * self.node_size
        x, y, z = struct.unpack_from("ddd", self._buffer, offset)
        target_bytes = bytes(self._buffer[offset + 24 : offset + 88]).rstrip(b"\x00")
        entropy = struct.unpack_from("d", self._buffer, offset + 88)[0]
        
        return {
            "x": x,
            "y": y,
            "z": z,
            "target": target_bytes.decode('utf-8', 'ignore'),
            "entropy": entropy
        }

if __name__ == "__main__":
    # C5-REAL Initialization Test
    umap = UltramapSubstrate()
    umap.update_agent_position(0, 10.0, 20.0, 30.0, "CVE-2026-MINIPLASMA", 0.95)
    joules = umap.calculate_exergy_distance(0, "TARGET_DARKPOOL_0x1")
    print(f"C5-REAL: Exergy Distance Calculated: {joules:.2f} Joules")
    print(f"Agent 0 State: {umap.get_agent_state(0)}")
