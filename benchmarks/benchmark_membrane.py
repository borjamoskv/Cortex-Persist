# [C5-REAL] Exergy-Maximized
import logging
import os
import sys

import torch  # pyright: ignore[reportMissingImports]
import torchhd  # pyright: ignore[reportMissingImports]

# Adjust path to import cortex module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babylon60.memory.epistemic_membrane import EpistemicMembrane

# Configure logging to write to stdout
logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_stress_test():
    logging.info("=== Epistemic Membrane Stress Test (C5-REAL) ===")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dim = 16384
    membrane = EpistemicMembrane(dim=dim, max_history=1000)

    logging.info(f"Device: {device}")
    logging.info(f"Membrane initialized. D={dim}, max_history={1000}")

    # 1. Establish base context (Genesis)
    logging.info("\n--- 1. Genesis & Normal Learning Phase ---")
    base_components = [
        ("subject", torchhd.random(1, dim, device=device)[0]),
        ("action", torchhd.random(1, dim, device=device)[0]),
        ("object", torchhd.random(1, dim, device=device)[0]),
    ]

    genesis_hv = membrane.encode_episode(base_components, timestep=0)
    membrane.commit(genesis_hv, metadata={"accept": True, "reason": "genesis"})
    logging.info("Genesis commit accepted.")

    # Normal learning: Small drift over 100 timesteps
    acceptances = 0
    recent_hvs = [genesis_hv]

    for _t in range(1, 101):
        # Small mutation on object (flip ~15% of bits -> similarity ~0.80)
        mutated_obj = base_components[2][1].clone()
        flip_mask = torch.rand(dim, device=device) < 0.15
        mutated_obj[flip_mask] = -mutated_obj[flip_mask]

        episode = [
            ("subject", base_components[0][1]),
            ("action", base_components[1][1]),
            ("object", mutated_obj),
        ]

        prop_hv = membrane.encode_episode(episode, timestep=0)
        check = membrane.check_proposal(prop_hv)

        if check["accept"]:
            membrane.commit(prop_hv, metadata=check)
            recent_hvs.append(prop_hv)
            acceptances += 1

    logging.info(f"Normal learning phase complete. Accepted {acceptances}/100 episodes.")
    logging.info(f"Ledger size: {len(membrane.ledger.leaves)}")

    # 2. Adversarial Injection
    logging.info("\n--- 2. Adversarial Injection Phase ---")
    # Completely random episode (Noise)
    adv_components = [
        ("subject", torchhd.random(1, dim, device=device)[0]),
        ("action", torchhd.random(1, dim, device=device)[0]),
        ("object", torchhd.random(1, dim, device=device)[0]),
    ]
    adv_hv = membrane.encode_episode(adv_components, timestep=101)
    check_adv = membrane.check_proposal(adv_hv)
    logging.info(f"Adversarial Proposal Check: {check_adv}")

    # 3. Inducing Epistemic Crisis & Autopoietic Mutation
    logging.info("\n--- 3. Epistemic Crisis Phase ---")
    # We simulate a paradigm shift by creating vectors that drift significantly from genesis
    # but remain internally coherent in recent history.
    crisis_hvs = []
    current_shift = genesis_hv.clone()
    for _t in range(102, 122):
        # accumulate 15% bit flips per step to force drift
        mask = torch.rand(dim, device=device) < 0.15
        current_shift[mask] = -current_shift[mask]
        crisis_hvs.append(current_shift.clone())

    logging.info("Triggering detect_and_mutate() on shifted paradigm...")
    mutation, meta = membrane.detect_and_mutate(crisis_hvs, generations=3)

    if mutation is not None:
        logging.info(f"Mutation triggered! Meta: {meta}")
        membrane.commit(mutation, metadata={"accept": True, "reason": "autopoietic_mutation"})
        logging.info(f"Mutant committed. Ledger root: {membrane.ledger._compute_root()}")
    else:
        logging.info("Coherence did not drop below threshold, no mutation needed.")

    logging.info("\n--- Benchmark Complete ---")


if __name__ == "__main__":
    run_stress_test()
