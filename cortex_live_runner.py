import time
import sys
import json
import logging
import uuid
import signal

# Clean logging for stdout piping
logging.getLogger("cortex").setLevel(logging.CRITICAL)

from cortex.runtime.disk_ledger import DiskLedger
from cortex.runtime.disk_snapshot import DiskSnapshotManager
from cortex.runtime.loop import RuntimeLoop
from cortex.runtime.recovery import RecoveryKernel
from cortex.runtime.state import RuntimeState

class LiveMetrics:
    """Sprint 4.5: Dashboard Observability Stream"""
    def emit(self, state: RuntimeState):
        metric = {
            "type": "STATE_METRIC",
            "state_hash": state.hash,
            "version": state.version,
            "entropy": state.data.get("entropy", 0.5),
            "psi": state.version * 0.1,  # Mock Epistemic Energy
            "timestamp": time.time()
        }
        sys.stdout.write(json.dumps(metric) + "\n")
        sys.stdout.flush()

def handle_sigterm(*args):
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    ledger = DiskLedger()
    snapshot = DiskSnapshotManager(interval=5)
    metrics = LiveMetrics()
    
    # 1. Recovery Sequence (Real Physical Boot)
    t0 = time.time()
    recovery = RecoveryKernel(ledger, snapshot)
    recovered_state = recovery.recover()
    replay_duration = time.time() - t0
    
    # Emit Recovery Topology for Chaos Harness validation
    sys.stdout.write(json.dumps({
        "type": "RECOVERY_METRIC",
        "replay_duration_ms": round(replay_duration * 1000, 2),
        "state_hash": recovered_state.hash,
        "version": recovered_state.version,
        "timestamp": time.time()
    }) + "\n")
    sys.stdout.flush()
    
    # 2. Live Execution
    loop = RuntimeLoop(ledger, metrics, snapshot)
    loop.start(injected_state=recovered_state)
