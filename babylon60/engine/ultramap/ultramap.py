import atexit
import logging
import mmap
import os
import struct
import weakref
from typing import Any

from babylon60.agents.primitives.dispatcher import apex_dispatcher
from babylon60.crypto.hash_registry import cortex_hash_truncated

logger = logging.getLogger("babylon60.ultramap")

try:
    import cortex_rs

    HAS_RUST = hasattr(cortex_rs, "UltramapSubstrate")
except ImportError as e:
    HAS_RUST = False
    logger.warning(f"Failed to load CORTEX-RS: {e}. Falling back to Python mmap.")

# Evolution Ledger — replay-safe mutation tracking
try:
    from babylon60.engine.checkpoint import CheckpointManager
    from babylon60.engine.evolution_ledger import ControlVector, EvolutionLedger

    HAS_EVOLUTION_LEDGER = True
except ImportError:
    HAS_EVOLUTION_LEDGER = False
    ControlVector = None  # type: ignore[assignment,misc]
    EvolutionLedger = None  # type: ignore[assignment,misc]
    CheckpointManager = None  # type: ignore[assignment,misc]

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

    Memory Layout per Node (128 bytes):
      [0:24]  : X, Y, Z coordinates (3x double)
      [24:88] : Target Hash (64 bytes string)
      [88:96] : Entropy Gradient (double)
      [96:128]: Control Vector (4x double: queue_depth, error_rate, causal_entropy, cpu_load)
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
            self._rs = cortex_rs.UltramapSubstrate(self.bin_path, self.capacity)  # type: ignore
            self._buffer = None
            self._mmap = None
            self._f = None
        else:
            self._rs = None
            self._f = open(self.bin_path, "r+b")
            self._mmap = mmap.mmap(self._f.fileno(), self.tensor_size)
            self._buffer = memoryview(self._mmap)

            self._finalizer = weakref.finalize(
                self,
                self._safe_close,
                getattr(self, "_buffer", None),
                getattr(self, "_mmap", None),
                getattr(self, "_f", None),
            )
            atexit.register(self.close)

        # Evolution Ledger — hash-chained mutation log
        self._evolution_ledger = None
        self._checkpoint_manager = None
        if HAS_EVOLUTION_LEDGER:
            ledger_path = os.path.join(os.path.dirname(self.bin_path), "evolution_ledger.jsonl")
            try:
                self._evolution_ledger = EvolutionLedger(ledger_path)  # type: ignore[misc]
                self._checkpoint_manager = CheckpointManager(
                    self._evolution_ledger, chunk_size=1000
                )  # type: ignore[misc]
                logger.info(
                    f"EVO-LEDGER Active. Head: {self._evolution_ledger.head_hash[:12]}… Seq: {self._evolution_ledger.sequence}"
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"EVO-LEDGER init failed (non-fatal): {e}")

        logger.info(
            f"ULTRAMAP-Ω Initialized. Capacity: {self.capacity} agents. O(1) Memory Active. (Rust: {HAS_RUST})"
        )

    @staticmethod
    def _safe_close(buffer_obj, mmap_obj, f_obj):
        try:
            if buffer_obj:
                buffer_obj.release()
            if mmap_obj:
                mmap_obj.close()
            if f_obj:
                f_obj.close()
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            try:
                logger.debug("Error in ultramap _safe_close: %s", e)
            except (OSError, ValueError, TypeError, RuntimeError):
                import logging

                logging.getLogger(__name__).error(
                    "DETECTIVE-OMEGA: Silent exception swallowed in ultramap.py"
                )

    def close(self):
        if hasattr(self, "_checkpoint_manager") and self._checkpoint_manager is not None:
            try:
                self._checkpoint_manager.generate_index()
                logger.info("EVO-LEDGER Checkpoints synced on shutdown.")
            except (OSError, ValueError, TypeError, RuntimeError) as e:
                logger.warning(f"EVO-LEDGER Checkpoint sync failed: {e}")
            self._checkpoint_manager = None

        if hasattr(self, "_finalizer") and self._finalizer.alive:
            self._finalizer.detach()
        if hasattr(self, "_rs") and self._rs is not None:
            self._rs = None
        if hasattr(self, "_buffer") and self._buffer is not None:
            try:
                self._buffer.release()
            except ValueError:
                import logging

                logging.getLogger(__name__).error(
                    "DETECTIVE-OMEGA: Silent exception swallowed in ultramap.py"
                )
            self._buffer = None
        if hasattr(self, "_mmap") and self._mmap is not None:
            try:
                self._mmap.close()
            except ValueError:
                import logging

                logging.getLogger(__name__).error(
                    "DETECTIVE-OMEGA: Silent exception swallowed in ultramap.py"
                )
            self._mmap = None
        if hasattr(self, "_f") and self._f is not None:
            try:
                self._f.close()
            except OSError:
                import logging

                logging.getLogger(__name__).error(
                    "DETECTIVE-OMEGA: Silent exception swallowed in ultramap.py"
                )
            self._f = None

    def update_agent_position(
        self, agent_idx: int, x: float, y: float, z: float, target: str, entropy: float
    ):
        """Updates the topological coordinates of a swarm agent."""
        if not (0 <= agent_idx < self.capacity):
            return False

        if self._rs is not None:
            return self._rs.update_agent_position(agent_idx, x, y, z, target, entropy)

        offset = agent_idx * self.node_size
        assert self._buffer is not None

        struct.pack_into("ddd", self._buffer, offset, x, y, z)  # pyright: ignore[reportArgumentType]
        target_bytes = target.encode("utf-8")[:64].ljust(64, b"\x00")
        self._buffer[offset + 24 : offset + 88] = target_bytes  # pyright: ignore[reportOptionalSubscript]
        struct.pack_into("d", self._buffer, offset + 88, entropy)  # pyright: ignore[reportArgumentType]

        return True

    def calculate_exergy_distance(self, agent_idx: int, target_hash: str) -> float:
        """
        O(1) calculation of thermodynamic distance to target.
        Returns the Joules required to traverse the topology.
        """
        if not (0 <= agent_idx < self.capacity):
            apex_dispatcher.execute("OP_APOPTOSIS")
            raise EntropyDeath("Agent Index Out of Bounds. Apoptosis triggered.")

        if self._rs is not None:
            return self._rs.calculate_exergy_distance(agent_idx, target_hash)

        offset = agent_idx * self.node_size
        assert self._buffer is not None
        x, y, z = struct.unpack_from("ddd", self._buffer, offset)  # pyright: ignore[reportArgumentType]
        current_entropy = struct.unpack_from("d", self._buffer, offset + 88)[0]  # pyright: ignore[reportArgumentType]

        target_int = int(cortex_hash_truncated(target_hash.encode(), length=16), 16)
        tx = (target_int % 1000) / 10.0
        ty = ((target_int >> 4) % 1000) / 10.0
        tz = ((target_int >> 8) % 1000) / 10.0

        distance = ((tx - x) ** 2 + (ty - y) ** 2 + (tz - z) ** 2) ** 0.5
        joules = distance * (1.0 / (current_entropy + 0.001))
        return joules

    def get_agent_state(self, agent_idx: int) -> dict:
        if not (0 <= agent_idx < self.capacity):
            return {}

        if self._rs is not None:
            return self._rs.get_agent_state(agent_idx)

        offset = agent_idx * self.node_size
        assert self._buffer is not None
        x, y, z = struct.unpack_from("ddd", self._buffer, offset)  # pyright: ignore[reportArgumentType]
        target_bytes = bytes(self._buffer[offset + 24 : offset + 88]).rstrip(b"\x00")  # pyright: ignore[reportOptionalSubscript]
        entropy = struct.unpack_from("d", self._buffer, offset + 88)[0]  # pyright: ignore[reportArgumentType]

        # UESS v2 Scalar Control Fields are stored at [96:128]
        queue_depth, error_rate, causal_entropy, cpu_load = struct.unpack_from(
            "dddd", self._buffer, offset + 96
        )  # pyright: ignore[reportArgumentType]

        raw_state = {
            "x": x,
            "y": y,
            "z": z,
            "target": target_bytes.decode("utf-8", "ignore"),
            "entropy": entropy,
            "queue_depth": queue_depth,
            "error_rate": error_rate,
            "causal_entropy": causal_entropy,
            "cpu_load": cpu_load,
        }

        # [C5-REAL] OP_FREEZE_MEM: Ensure structural immutability of the returned map.
        return apex_dispatcher.execute("OP_FREEZE_MEM", state=raw_state)

    def update_control_vector(
        self,
        agent_idx: int,
        queue_depth: float,
        error_rate: float,
        causal_entropy: float,
        cpu_load: float,
        *,
        source: str = "substrate",
    ) -> bool:
        """UESS v2: Writes the Control Vector fields to the memory substrate.

        Every mutation is recorded to the Evolution Ledger (hash-chained JSONL)
        for replay-safe auditing. The 'source' kwarg identifies the caller.
        """
        if self._rs is not None:
            success = self._rs.update_control_vector(
                agent_idx, queue_depth, error_rate, causal_entropy, cpu_load
            )
            if success and self._evolution_ledger is not None:
                self._emit_ledger_event(
                    agent_idx, None, queue_depth, error_rate, causal_entropy, cpu_load, source
                )
            return success

        if not (0 <= agent_idx < self.capacity):
            return False

        offset = agent_idx * self.node_size
        assert self._buffer is not None
        x, y, z = struct.unpack_from("ddd", self._buffer, offset)  # pyright: ignore[reportArgumentType]
        if x == 0.0 and y == 0.0 and z == 0.0:
            return False

        # Capture before-state for ledger
        vector_before = None
        if self._evolution_ledger is not None:
            try:
                qd_b, er_b, ce_b, cl_b = struct.unpack_from("dddd", self._buffer, offset + 96)  # pyright: ignore[reportArgumentType]
                vector_before = ControlVector(qd_b, er_b, ce_b, cl_b)  # type: ignore[misc]
            except (struct.error, TypeError):
                pass

        # Write to substrate
        struct.pack_into(
            "dddd", self._buffer, offset + 96, queue_depth, error_rate, causal_entropy, cpu_load
        )  # pyright: ignore[reportArgumentType]

        # Emit to Evolution Ledger
        if self._evolution_ledger is not None:
            self._emit_ledger_event(
                agent_idx, vector_before, queue_depth, error_rate, causal_entropy, cpu_load, source
            )

        return True

    def _emit_ledger_event(
        self,
        agent_idx: int,
        vector_before: Any,
        queue_depth: float,
        error_rate: float,
        causal_entropy: float,
        cpu_load: float,
        source: str,
    ) -> None:
        """Emit a mutation record to the Evolution Ledger. Non-fatal on error."""
        try:
            vector_after = ControlVector(queue_depth, error_rate, causal_entropy, cpu_load)  # type: ignore[misc]
            self._evolution_ledger.record_mutation(  # type: ignore[misc,attr-defined]
                agent_idx=agent_idx,
                vector_before=vector_before,
                vector_after=vector_after,
                source=source,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"EVO-LEDGER write failed (non-fatal): {e}")


if __name__ == "__main__":
    umap = UltramapSubstrate()
    umap.update_agent_position(0, 10.0, 20.0, 30.0, "CVE-2026-MINIPLASMA", 0.95)

    # UESS v2: update agent control vector
    success = umap.update_control_vector(
        0, queue_depth=10.0, error_rate=0.05, causal_entropy=0.1, cpu_load=0.6
    )

    joules = umap.calculate_exergy_distance(0, "TARGET_DARKPOOL_0x1")
    logger.info(f"C5-REAL: Exergy Distance Calculated: {joules:.2f} Joules")
    logger.info(f"UESS v2 Update Success: {success}")
    logger.info(f"Agent 0 State: {umap.get_agent_state(0)}")
