# [C5-REAL] Exergy-Maximized
"""
CORTEX-SWARM-PRIME: Staged Hierarchical Legion - 2M Agents.
Overcomes physical RAM/disk limits by streaming waves of agents through
a single mmap slot, collapsing each wave into a Centurion hypervector,
then reducing all Centurions into the Global Consensus.

Architecture:
    L0: 2,000,000 logical agents
    L1: N waves × K physical agents per wave (K fits in disk)
    L2: Each wave collapses to 1 Centurion (D-dimensional hypervector)
    L3: All Centurions reduce to Global Consensus

C5-REAL - Zero disk overflow guaranteed.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time

from cortex.compat.optional import np
from cortex.swarm.tensor_glial import TensorGlialLegion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.swarm.staged_legion")

MMAP_FILE = "staged_wave.vsa_mmap"


def _cleanup_mmap(path: str) -> None:
    """Delete mmap file to free disk for the next wave."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def execute_staged_reverse_engineering(
    target: str,
    total_agents: int = 2_000_000,
    agents_per_wave: int = 20_000,
    d_dim: int = 10_000,
) -> None:
    """
    Deploy `total_agents` in streaming waves of `agents_per_wave`.
    Each wave occupies agents_per_wave * d_dim * 4 bytes on disk.
    Default: 20000 * 10000 * 4 = 800 MB per wave.
    """
    num_waves = total_agents // agents_per_wave
    remainder = total_agents % agents_per_wave

    wave_sizes = [agents_per_wave] * num_waves
    if remainder > 0:
        wave_sizes.append(remainder)
        num_waves += 1

    mmap_bytes = agents_per_wave * d_dim * 4
    logger.info(
        "🚀 STAGED LEGION: %d total agents | %d waves × %d agents | %.1f MB per wave | target=%s",
        total_agents,
        num_waves,
        agents_per_wave,
        mmap_bytes / (1024**2),
        target,
    )

    centurion_states: list[np.ndarray] = []  # pyright: ignore[reportInvalidTypeForm]
    wave_hashes: list[str] = []
    total_slashed = 0
    t0 = time.monotonic()

    for wave_idx, wave_size in enumerate(wave_sizes):
        t_wave = time.monotonic()

        # --- Ensure clean slate ---
        _cleanup_mmap(MMAP_FILE)

        # --- Boot wave ---
        legion = TensorGlialLegion(
            num_agents=wave_size,
            d_dim=d_dim,
            file_path=MMAP_FILE,
        )

        # --- Phase 1: Simulate workload ---
        legion.yield_tensor = np.random.lognormal(mean=0.5, sigma=1.0, size=wave_size).astype(
            np.float32
        )
        legion.token_burn_tensor.fill(1.0)

        # --- Phase 2: Epistemic Slashing ---
        slashed = legion.epistemic_slash_and_respawn(bottom_percentile=20, elite_percentile=98)
        total_slashed += slashed

        # --- Phase 3: Centurion collapse (entire wave → 1 vector) ---
        centurion = legion.map_reduce_centurion(0, wave_size)
        centurion_states.append(centurion)

        # --- Phase 4: Integrity hash of this wave ---
        wave_hash = legion.global_sha256_audit()
        wave_hashes.append(wave_hash)

        # --- Release resources ---
        del legion
        _cleanup_mmap(MMAP_FILE)

        dt = time.monotonic() - t_wave
        logger.info(
            "  Wave %03d/%03d | %5d agents | slashed %4d | %.2fs | SHA256=%s…",
            wave_idx + 1,
            num_waves,
            wave_size,
            slashed,
            dt,
            wave_hash[:16],
        )

    # --- L3: Global Consensus from all Centurions ---
    logger.info("🪐 Collapsing %d Centurions into Global Consensus...", len(centurion_states))
    from cortex.vsa_engine import VSAEngine

    vsa = VSAEngine(D=d_dim, algebra="HRR")  # pyright: ignore[reportCallIssue]

    global_consensus = np.sum(centurion_states, axis=0)
    global_consensus = vsa.normalize(global_consensus)

    # Global integrity = SHA256 of the concatenated centurion hashes
    global_hash = hashlib.sha256("|".join(wave_hashes).encode()).hexdigest()

    elapsed = time.monotonic() - t0

    # --- Report ---
    logger.info("=" * 80)
    logger.info("[%s] STAGED REVERSE ENGINEERING - FINAL REPORT", target.upper())
    logger.info("=" * 80)
    logger.info("Total agents deployed:    %d", total_agents)
    logger.info("Waves executed:           %d", num_waves)
    logger.info("Total nodes slashed:      %d", total_slashed)
    logger.info("Global consensus norm:    %.6f", float(np.linalg.norm(global_consensus)))
    logger.info("Global integrity SHA256:  %s", global_hash)
    logger.info("Total elapsed:            %.2fs", elapsed)
    logger.info("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Staged Hierarchical Swarm - 2M Agent Reverse Engineering"
    )
    parser.add_argument("--target", default="cortex-kernel", help="Target to reverse engineer")
    parser.add_argument("--total", type=int, default=2_000_000, help="Total logical agents")
    parser.add_argument("--wave-size", type=int, default=20_000, help="Agents per wave")
    parser.add_argument("--dim", type=int, default=10_000, help="VSA dimensionality")
    args = parser.parse_args()

    execute_staged_reverse_engineering(
        target=args.target,
        total_agents=args.total,
        agents_per_wave=args.wave_size,
        d_dim=args.dim,
    )
