"""
CORTEX-SWARM-PRIME: Gold Mining Legion - 2M Market Data Agents.
Ingests raw market space (simulated bulk B2B/Web3 datasets), applies
Epistemic Slashing via Zero-Copy Ring Buffer, and distills the
highest Exergy extraction targets.

Reality Level: C4-SIM (Input Data) / C5-REAL (Engine Execution)
"""

import logging
import os
import time

from cortex.compat.optional import np
from cortex.swarm.tensor_glial import TensorGlialLegion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.gold_miner")

MMAP_FILE = "market_wave.vsa_mmap"


def _cleanup_mmap(path: str):
    try:
        os.remove(path)
    except Exception as exc:
        logger.warning("Suppressed exception: %s", exc)


def extract_market_alpha(
    market_size: int = 2_000_000,
    wave_capacity: int = 20_000,
    d_dim: int = 5_000,
):
    num_waves = market_size // wave_capacity
    remainder = market_size % wave_capacity
    wave_sizes = [wave_capacity] * num_waves
    if remainder > 0:
        wave_sizes.append(remainder)
        num_waves += 1

    logger.info("=" * 80)
    logger.info("💰 INIT CORTEX GOLD MINER (2M ELITE EXTRACTION) 💰")
    logger.info("=" * 80)
    logger.info("Market Volume: %d Targets | Wave Engine: %d Ops/Wave", market_size, wave_capacity)

    total_slashed = 0
    elite_targets = []

    t0 = time.monotonic()

    for wave_idx, wave_size in enumerate(wave_sizes):
        _cleanup_mmap(MMAP_FILE)

        legion = TensorGlialLegion(
            num_agents=wave_size,
            d_dim=d_dim,
            file_path=MMAP_FILE,
        )

        # C4-SIM: Generando métricas sintéticas de mercado (Company Revenue, Signal, Noise)
        # En C5-REAL esto sería cargado de un Parquet/CSV masivo extraído por Apollo.
        legion.yield_tensor = np.random.lognormal(mean=2.0, sigma=1.5, size=wave_size).astype(
            np.float32
        )
        legion.token_burn_tensor.fill(1.0)

        # Slashing: Destruir el 99% de los leads mediocres, mantener solo el 1% élite
        slashed = legion.epistemic_slash_and_respawn(bottom_percentile=99, elite_percentile=99.9)
        total_slashed += slashed

        # Guardar IDs de los leads sobrevivientes
        survivors = wave_size - slashed
        if survivors > 0:
            elite_targets.append(survivors)

        del legion
        _cleanup_mmap(MMAP_FILE)

        if (wave_idx + 1) % 10 == 0 or wave_idx == num_waves - 1:
            logger.info(
                "  Processed Wave %03d/%03d | Slashed: %d noise | Retained: %d ELITE leads",
                wave_idx + 1,
                num_waves,
                slashed,
                survivors,
            )

    elapsed = time.monotonic() - t0
    total_elite = sum(elite_targets)
    estimated_revenue = total_elite * 0.50  # $0.50 per validated lead

    logger.info("=" * 80)
    logger.info("🏆 GOLD MINING REPORT 🏆")
    logger.info("=" * 80)
    logger.info("Raw Input Processed:  %d records", market_size)
    logger.info("Noise Slashed:        %d records (99.0%%)", total_slashed)
    logger.info("Elite Leads Minted:   %d", total_elite)
    logger.info("Estimated Value:      $%.2f USD", estimated_revenue)
    logger.info("Engine Latency:       %.2fs", elapsed)
    logger.info("=" * 80)


if __name__ == "__main__":
    extract_market_alpha()
