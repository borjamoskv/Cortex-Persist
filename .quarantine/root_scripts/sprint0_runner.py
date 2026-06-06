# [C5-REAL] Exergy-Maximized
import logging
import sys
import time

# Configure logging to look like an Industrial OS
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | CORTEX-%(name)-8s | %(message)s", datefmt="%H:%M:%S"
)

from cortex.runtime.loop import RuntimeLoop
from cortex.runtime.snapshot import SnapshotManager
from cortex.runtime.recovery import RecoveryKernel
from cortex.runtime.state import RuntimeState


class MockLedger:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)

    def query_from(self, version: int):
        # State version corresponds to number of events in this mock
        return self.events[version:]


class MockMetrics:
    def emit(self, state: RuntimeState):
        sys.stdout.write(
            f"\r[EMIT] Event Processed | SSU: {state.version * 0.1:.2f} | Hash: {state.hash[:8]}... "
        )
        sys.stdout.flush()


if __name__ == "__main__":
    ledger = MockLedger()
    metrics = MockMetrics()
    snapshot = SnapshotManager(interval=5)  # Fast snapshot for testing

    print("\n--- CORTEX SPRINT 0: RUNTIME KERNEL ---")
    print("Press Ctrl+C to simulate a BRUTAL PROCESS KILL.\n")

    loop = RuntimeLoop(ledger, metrics, snapshot)

    try:
        # Phase 1: Normal Execution (Auto-kill after 6s for demo)
        import threading

        def brutal_kill():
            time.sleep(6)
            import _thread

            _thread.interrupt_main()

        threading.Thread(target=brutal_kill, daemon=True).start()

        loop.start()
    except KeyboardInterrupt:
        print("\n\n--- INITIATING SPRINT 2 RECOVERY SEQUENCE ---")
        time.sleep(1)

        # Phase 2: Recovery Boot
        recovery = RecoveryKernel(ledger, snapshot)
        recovered_state = recovery.recover()

        print("\n--- RESUMING CAUSAL EXECUTION ---")
        time.sleep(1)

        # Auto-kill Phase 2 after 3 seconds to exit script gracefully
        def graceful_exit():
            time.sleep(3)
            loop.is_running = False

        threading.Thread(target=graceful_exit, daemon=True).start()

        loop.start(injected_state=recovered_state)
