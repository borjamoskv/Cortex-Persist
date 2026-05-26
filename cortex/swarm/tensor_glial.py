"""
CORTEX-SWARM-PRIME: Tensor-Glial Legion
Zero-Copy `mmap` tensor map mapped across 10,000 swarm agents representing High-Dimensional Memory.
"""

import hashlib
import logging
import os
import threading
import time

from cortex.compat.optional import np  # lazy: pip install cortex-persist[compute]

try:
    from numba import njit, prange

    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

from cortex.vsa_engine import VSAEngine

# --- Direct-Silicon JIT Kernels ---
if HAS_NUMBA:

    @njit(parallel=True, fastmath=True)
    def fast_fading_memory(tensor_view, last_update_ts, now_ts, lambda_decay):
        for i in prange(tensor_view.shape[0]):
            dt = now_ts - last_update_ts[i]
            if dt < 0:
                dt = 0.0
            decay = np.exp(-lambda_decay * dt)
            for j in range(tensor_view.shape[1]):
                tensor_view[i, j] *= decay
            last_update_ts[i] = now_ts
else:

    def fast_fading_memory(tensor_view, last_update_ts, now_ts, lambda_decay):
        dt = np.clip(now_ts - last_update_ts, 0, None)
        decay = np.exp(-lambda_decay * dt)[:, np.newaxis]
        tensor_view *= decay
        last_update_ts.fill(now_ts)


class TensorGlialLegion:
    """
    Massive multiplexer for 10,000 CORTEX-Swarm-Prime agents.
    Uses zero-copy np.memmap to allocate (10000, 10000) VSA states contiguously in a binary flat file,
    aniquilating SQLite/JSON latency and allowing bulk Ebbinghaus decay and Batched MapReduce evaluations via GPU/SIMD.
    """

    def __init__(
        self, num_agents: int = 10000, d_dim: int = 10000, file_path: str = "tensor_legion.vsa_mmap"
    ):
        self.num_agents = num_agents
        self.D = d_dim
        self.file_path = file_path
        self.vsa = VSAEngine(D=self.D, algebra="HRR")

        # OMEGA-X Matrix Memory: shape (N, D), float64 = N*D*8 bytes
        # N=10000, D=10000 -> 800MB mapped straight to RAM (Zero-Copy)
        init_required = not os.path.exists(self.file_path)
        self.agents_tensor = np.memmap(
            self.file_path,
            dtype="float64",
            mode="w+" if init_required else "r+",
            shape=(self.num_agents, self.D),
        )

        # Parallel arrays for yield tracking and autopoiesis (epistemic slashing)
        self.yield_tensor = np.zeros(self.num_agents, dtype="float32")  # Compound Yield
        self.token_burn_tensor = np.zeros(self.num_agents, dtype="float32")
        self.last_update_ts = np.full(self.num_agents, time.time(), dtype="float64")

    def apply_fading_memory(self, lambda_decay: float = 0.001):
        """
        Glial Daemon: applies time-based Ebbinghaus forgetting universally across the 10,000x10,000 tensor.
        Executes via Direct-Silicon JIT (Numba) if available to bypass the GIL.
        """
        now = time.time()
        fast_fading_memory(self.agents_tensor, self.last_update_ts, now, lambda_decay)
        self.async_flush()

    def async_flush(self):
        """Asynchronous disk sync to prevent blocking the OMEGA-X orchestrator."""
        threading.Thread(target=self.agents_tensor.flush, daemon=True).start()

    def batch_write_action(self, agent_indices: list[int], action_texts: list[str]):
        """
        Batches N agents encoding real-time actions.
        """
        encoded_vecs = []
        for text in action_texts:
            encoded_vecs.append(self.vsa.encode_text(text))

        # Add to the sum tensor directly
        vsa_vecs = np.array(encoded_vecs)
        self.agents_tensor[agent_indices] += vsa_vecs
        self.agents_tensor[agent_indices] = self.normalize_batch(self.agents_tensor[agent_indices])

        now = time.time()
        self.last_update_ts[agent_indices] = now
        self.async_flush()

    def normalize_batch(self, batch: np.ndarray) -> np.ndarray:
        """Batch normalize row by row."""
        norms = np.linalg.norm(batch, axis=1, keepdims=True)
        norms[norms < 1e-12] = 1.0  # Prevent division by zero
        return batch / norms

    def map_reduce_centurion(self, start_idx: int, end_idx: int) -> np.ndarray:
        """
        MapReduce Topologico: L2 Centurions collapse 100 subordinate agents into a single 1D tensor
        to send up to the LegionSupervisor, saving 99% bandwidth.
        """
        squad_block = self.agents_tensor[start_idx:end_idx]
        superposition = np.sum(squad_block, axis=0)  # Sum across rows
        return self.vsa.normalize(superposition)

    def epistemic_slash_and_respawn(
        self, bottom_percentile: float = 10.0, elite_percentile: float = 95.0
    ):
        """
        C5 Epistemic Slashing:
        Agrega Autopoiesis matando a los nodos inertes (rendimiento basura < bottom_percentile).
        Renacen con la topología/mutación VSA del elite top_percentile.
        """
        yield_ratio = self.yield_tensor / (self.token_burn_tensor + 1e-5)

        # Find elites
        p_elite = np.percentile(yield_ratio, elite_percentile)
        elite_indices = np.where(yield_ratio >= p_elite)[0]
        if len(elite_indices) == 0:
            return 0  # Not enough data

        # Find corpses
        p_bottom = np.percentile(yield_ratio, bottom_percentile)
        corpse_indices = np.where(yield_ratio <= p_bottom)[0]

        # Respawner: Death and Rebirth without creating new Python objects
        respawn_count = 0
        for i, corpse_idx in enumerate(corpse_indices):
            elite_idx = elite_indices[i % len(elite_indices)]
            # Genetic inheritance + stochastic perturbation
            mutation = np.random.normal(0, 0.05, size=self.D)
            new_vsa = self.agents_tensor[elite_idx] + mutation

            # Reset
            self.agents_tensor[corpse_idx] = self.vsa.normalize(new_vsa)
            self.yield_tensor[corpse_idx] = 0.0
            self.token_burn_tensor[corpse_idx] = 0.0
            self.last_update_ts[corpse_idx] = time.time()
            respawn_count += 1

        self.async_flush()
        return respawn_count

    def global_sha256_audit(self) -> str:
        """
        CORTEX Filter 5: Persistence - Check SHA256 of the 10000x10000 memory space lock.
        """
        self.agents_tensor.flush()
        with open(self.file_path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()


if __name__ == "__main__":
    # Boot sequence for local execution validation
    logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger("cortex.swarm.tensor_glial")
    _log.info("Legión TensorGlial init...")
    # Fast test with 100 agents, 1000 D for speed
    legion = TensorGlialLegion(num_agents=100, d_dim=1000, file_path="tmp_legion.vsa_mmap")

    start_time = time.time()
    # Apply glial memory fading over total batch
    legion.apply_fading_memory(lambda_decay=0.01)

    # 10 Nodes get struck and mutate
    legion.yield_tensor[0:10] = 0.0  # pure garbage yield
    legion.yield_tensor[90:100] = 100.0  # elite yield
    legion.token_burn_tensor.fill(1.0)

    slashed = legion.epistemic_slash_and_respawn(bottom_percentile=10, elite_percentile=90)

    # Reduce
    centurion_state = legion.map_reduce_centurion(0, 100)

    _log.info("Total execution time: %.4fs", time.time() - start_time)
    _log.info("Nodes respawned from corpses: %d", slashed)
    _log.info("Centurion MapReduce state dim: %s", centurion_state.shape)
    _log.info("Matrix SHA256 integrity: %s", legion.global_sha256_audit())
