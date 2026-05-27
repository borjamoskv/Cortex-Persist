import os
import mmap
import time
import struct
import hashlib
import logging
import weakref
import atexit

logger = logging.getLogger("cortex.ultramap")

try:
    import cortex_rs
    HAS_RUST = True
except ImportError as e:
    HAS_RUST = False
    logger.warning(f"Failed to load CORTEX-RS: {e}. Falling back to Python mmap.")

DB_PATH = os.getenv(
    "CORTEX_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cortex_memory_vsa.db"),
)

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
        self.node_size = 128
        self.tensor_size = self.capacity * self.node_size
        self.bin_path = os.path.join(os.path.dirname(DB_PATH), "ultramap.bin")

        if not os.path.exists(self.bin_path) or os.path.getsize(self.bin_path) < self.tensor_size:
            os.makedirs(os.path.dirname(self.bin_path), exist_ok=True)
            with open(self.bin_path, "wb") as f:
                f.write(b"\x00" * self.tensor_size)

        if HAS_RUST:
            try:
                self._rs = cortex_rs.UltramapSubstrate(self.bin_path, self.capacity)
            except AttributeError:
                self._rs = None
            self._buffer = None
            self._mmap = None
            self._f = None
        else:
            self._rs = None
            self._f = open(self.bin_path, "r+b")
            self._mmap = mmap.mmap(self._f.fileno(), self.tensor_size)
            self._buffer = memoryview(self._mmap)
            
            self._finalizer = weakref.finalize(self, self._safe_close, getattr(self, '_buffer', None), getattr(self, '_mmap', None), getattr(self, '_f', None))
            atexit.register(self.close)
        
        logger.info(f"ULTRAMAP-Ω Initialized. Capacity: {self.capacity} agents. O(1) Memory Active. (Rust: {HAS_RUST})")

    @staticmethod
    def _safe_close(buffer_obj, mmap_obj, f_obj):
        try:
            if buffer_obj:
                buffer_obj.release()
            if mmap_obj:
                mmap_obj.close()
            if f_obj:
                f_obj.close()
        except Exception as e:
            try:
                logger.debug("Error in ultramap _safe_close: %s", e)
            except Exception:
                pass

    def close(self):
        if hasattr(self, "_finalizer") and self._finalizer.alive:
            self._finalizer.detach()
        if hasattr(self, "_rs") and self._rs is not None:
            self._rs = None
        if hasattr(self, "_buffer") and self._buffer is not None:
            try:
                self._buffer.release()
            except ValueError:
                pass
            self._buffer = None
        if hasattr(self, "_mmap") and self._mmap is not None:
            try:
                self._mmap.close()
            except ValueError:
                pass
            self._mmap = None
        if hasattr(self, "_f") and self._f is not None:
            try:
                self._f.close()
            except OSError:
                pass
            self._f = None

    def update_agent_position(self, agent_idx: int, x: float, y: float, z: float, target: str, entropy: float):
        """Updates the topological coordinates of a swarm agent."""
        if not (0 <= agent_idx < self.capacity):
            return False
            
        if self._rs is not None:
            return self._rs.update_agent_position(agent_idx, x, y, z, target, entropy)

        offset = agent_idx * self.node_size
        
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
            
        if self._rs is not None:
            return self._rs.calculate_exergy_distance(agent_idx, target_hash)

        offset = agent_idx * self.node_size
        x, y, z = struct.unpack_from("ddd", self._buffer, offset)
        current_entropy = struct.unpack_from("d", self._buffer, offset + 88)[0]
        
        target_int = int(hashlib.sha256(target_hash.encode()).hexdigest()[:16], 16)
        tx = (target_int % 1000) / 10.0
        ty = ((target_int >> 4) % 1000) / 10.0
        tz = ((target_int >> 8) % 1000) / 10.0
        
        distance = ((tx - x)**2 + (ty - y)**2 + (tz - z)**2)**0.5
        joules = distance * (1.0 / (current_entropy + 0.001))
        return joules
        
    def get_agent_state(self, agent_idx: int) -> dict:
        if not (0 <= agent_idx < self.capacity):
            return {}
            
        if self._rs is not None:
            return self._rs.get_agent_state(agent_idx)

        offset = agent_idx * self.node_size
        x, y, z = struct.unpack_from("ddd", self._buffer, offset)
        target_bytes = bytes(self._buffer[offset + 24 : offset + 88]).rstrip(b"\x00")
        entropy = struct.unpack_from("d", self._buffer, offset + 88)[0]
        
        # Hormones are stored at [96:128]
        dopamine, cortisol, serotonin, adrenaline = struct.unpack_from("dddd", self._buffer, offset + 96)
        
        return {
            "x": x,
            "y": y,
            "z": z,
            "target": target_bytes.decode('utf-8', 'ignore'),
            "entropy": entropy,
            "dopamine": dopamine,
            "cortisol": cortisol,
            "serotonin": serotonin,
            "adrenaline": adrenaline
        }

    def volume_transmit_hormones(self, origin_x: float, origin_y: float, origin_z: float, radius: float, dopamine: float, cortisol: float, serotonin: float, adrenaline: float) -> int:
        """Topographical Endocrinology: Volume transmission of hormones across the spatial matrix."""
        if self._rs is not None:
            return self._rs.volume_transmit_hormones(origin_x, origin_y, origin_z, radius, dopamine, cortisol, serotonin, adrenaline)
            
        affected = 0
        for i in range(self.capacity):
            offset = i * self.node_size
            x, y, z = struct.unpack_from("ddd", self._buffer, offset)
            if x == 0.0 and y == 0.0 and z == 0.0:
                continue
                
            dist = ((x - origin_x)**2 + (y - origin_y)**2 + (z - origin_z)**2)**0.5
            if dist <= radius and radius > 0.0:
                intensity = 1.0 - (dist / radius)
                d, c, s, a = struct.unpack_from("dddd", self._buffer, offset + 96)
                
                d = max(0.0, min(1.0, d + (dopamine * intensity)))
                c = max(0.0, min(1.0, c + (cortisol * intensity)))
                s = max(0.0, min(1.0, s + (serotonin * intensity)))
                a = max(0.0, min(1.0, a + (adrenaline * intensity)))
                
                struct.pack_into("dddd", self._buffer, offset + 96, d, c, s, a)
                affected += 1
                
        return affected

if __name__ == "__main__":
    umap = UltramapSubstrate()
    umap.update_agent_position(0, 10.0, 20.0, 30.0, "CVE-2026-MINIPLASMA", 0.95)
    
    # Simulate a topographical dopamine/adrenaline burst at origin (10.0, 20.0, 30.0) with radius 5.0
    affected = umap.volume_transmit_hormones(10.0, 20.0, 30.0, 5.0, dopamine=0.8, cortisol=0.0, serotonin=0.0, adrenaline=0.5)
    
    joules = umap.calculate_exergy_distance(0, "TARGET_DARKPOOL_0x1")
    logger.info(f"C5-REAL: Exergy Distance Calculated: {joules:.2f} Joules")
    logger.info(f"Topographical Endocrinology: Transmitted to {affected} agents.")
    logger.info(f"Agent 0 State: {umap.get_agent_state(0)}")
