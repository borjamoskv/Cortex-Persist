import time
import pytest
import torch
torchhd = pytest.importorskip("torchhd")
from cortex.memory.epistemic_membrane import EpistemicMembrane, MerkleLedger

def test_ledger_performance_o1():
    """
    Asserts that appending elements to the MerkleLedger scales in O(1) time
    and does not degrade quadratically as the history grows.
    """
    ledger = MerkleLedger()
    dim = 1000
    hv_sample = torchhd.random(1, dim)[0]

    # Warmup
    for _ in range(50):
        ledger.append(hv_sample, {"accept": True})

    # Measure append operations
    start_time = time.perf_counter()
    for _ in range(500):
        ledger.append(hv_sample, {"accept": True})
    elapsed_500 = time.perf_counter() - start_time

    # Add 2000 more elements to grow list size significantly
    for _ in range(2000):
        ledger.append(hv_sample, {"accept": True})

    # Measure append operations with larger size
    start_time = time.perf_counter()
    for _ in range(500):
        ledger.append(hv_sample, {"accept": True})
    elapsed_2500 = time.perf_counter() - start_time

    # O(1) implies the time ratio should be very close, safely bounded
    # Even with overhead, a linear scaling O(N) would be noticeably slower.
    # We assert the larger size execution is not slower by a factor of 3.
    assert elapsed_2500 < elapsed_500 * 3.0


def test_epistemic_membrane_parameters_and_device():
    """
    Asserts device alignment and parameter customization in EpistemicMembrane.
    """
    custom_device = torch.device("cpu")
    membrane = EpistemicMembrane(
        dim=1000,
        threshold_consistency=0.75,
        threshold_novelty=0.90,
        noise_tolerance=0.10,
        device=custom_device
    )

    assert membrane.threshold_consistency == 0.75
    assert membrane.threshold_novelty == 0.90
    assert membrane.noise_tolerance == 0.10
    assert membrane.device == custom_device
    assert membrane.roles["consistency"].device == custom_device


if __name__ == "__main__":
    print("Running performance test...")
    test_ledger_performance_o1()
    print("Running parameters and device test...")
    test_epistemic_membrane_parameters_and_device()
    print("All tests passed.")

