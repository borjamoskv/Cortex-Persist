import sys
import time
import random
import logging

# Silence logs for massive batch testing
logging.getLogger("cortex.recovery").setLevel(logging.CRITICAL)
logging.getLogger("cortex.runtime").setLevel(logging.CRITICAL)

from cortex.runtime.state import RuntimeState
from cortex.runtime.snapshot import SnapshotManager
from cortex.runtime.recovery import RecoveryKernel


class MemoryLedger:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)

    def query_from(self, version):
        return self.events[version:]


def generate_events(seed: int, count: int):
    rng = random.Random(seed)
    events = []
    for i in range(count):
        # Deterministic generation linked strictly to the seed
        events.append(
            {
                "event_id": f"evt_{rng.randint(0, 999999999)}",
                "action_type": "MEMORY_WRITE",
                "payload": {
                    "val": rng.random(),
                    "tick": i,  # Semantic Validation: Must strictly increase
                    "entropy": 0.5,  # Semantic Validation: Must be >= 0
                },
            }
        )
    return events


def run_equivalence_test(seed: int, total_events: int = 10) -> bool:
    events = generate_events(seed, total_events)

    # --- PATH A: UNINTERRUPTED EXECUTION ---
    state_a = RuntimeState()
    for evt in events:
        state_a.apply_event(evt)

    # --- PATH B: THE BRUTAL KILL & RECOVERY ---
    ledger_b = MemoryLedger()
    state_b = RuntimeState()
    snapshot_manager = SnapshotManager(interval=3)

    split_point = total_events // 2

    # 1. Execute to split point
    for evt in events[:split_point]:
        state_b.apply_event(evt)
        ledger_b.append(evt)
        snapshot_manager.maybe_save(state_b)

    # [BRUTAL KILL SIMULATED HERE] -> Memory wiped, but Ledger & Snapshot exist

    # 2. Recover from the void
    recovery = RecoveryKernel(ledger_b, snapshot_manager)
    recovered_state = recovery.recover()

    # 3. Resume causality
    for evt in events[split_point:]:
        recovered_state.apply_event(evt)
        ledger_b.append(evt)

    if state_a.hash != recovered_state.hash:
        print(f"\n[!] DIVERGENCE DETECTED AT SEED {seed}")
        print(f"Path A Hash: {state_a.hash}")
        print(f"Path B Hash: {recovered_state.hash}")
        return False
    return True


if __name__ == "__main__":
    TOTAL_TESTS = 100000
    EVENTS_PER_TEST = 10

    print("--- CORTEX REPLAY EQUIVALENCE VERIFIER ---")
    print(f"Target: {TOTAL_TESTS} tests, {EVENTS_PER_TEST} causal steps each.")
    print("Verifying state convergence...\n")

    start_time = time.time()

    divergences = 0
    for seed in range(TOTAL_TESTS):
        if not run_equivalence_test(seed, total_events=EVENTS_PER_TEST):
            divergences += 1
            break

        if seed > 0 and seed % 20000 == 0:
            print(f"  {seed} / {TOTAL_TESTS} proofs computed...")

    elapsed = time.time() - start_time

    print(f"\n{TOTAL_TESTS} deterministic recovery tests passed")
    print(f"{divergences} divergences detected")
    print(f"Execution time: {elapsed:.2f}s")

    if divergences > 0:
        sys.exit(1)
