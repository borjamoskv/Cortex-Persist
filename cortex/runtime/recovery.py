# [C5-REAL] Exergy-Maximized
import logging
from typing import Any

from .snapshot import SnapshotManager
from .state import RuntimeState

logger = logging.getLogger("cortex.recovery")


class RecoveryKernel:
    """Rebuilds reality from the void."""

    def __init__(self, ledger: Any, snapshot_manager: SnapshotManager):
        self.ledger = ledger
        self.snapshot_manager = snapshot_manager

    def recover(self) -> RuntimeState:
        # 1. Locate Anchor (Snapshot)
        state = self.snapshot_manager.load_latest()
        if not state:
            logger.warning("[!] No snapshot found. Bootstrapping reality from v0.")
            state = RuntimeState()
        else:
            logger.info(f"[+] Loaded Snapshot | Version: {state.version} | Hash: {state.hash}")

        # 2. Replay causality strictly forward
        pending_events = self.ledger.query_from(state.version)
        if pending_events:
            logger.info(f"[~] Replaying {len(pending_events)} orphaned events...")

        for event in pending_events:
            state.apply_event(event)

        logger.info(f"[✓] Recovery Complete | Final Hash: {state.hash}")
        return state
